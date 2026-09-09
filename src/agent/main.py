"""
FastAPI backend for the Cartmind agent.

Run with:
    uvicorn main:app --reload

This file only *exposes* the existing terminal agent (src/agent/agent.py) and
the existing RAG ingestion pipeline (src/rag/*) over HTTP. No logic inside
src/ was changed beyond src/agent/agent.py's new resume support, and the
new src/observability/request_logging.py module (structured per-request
JSON-Lines logging - see docstring there).

Endpoints
---------
GET    /api/health                        liveness check
POST   /api/chat                          send a message, get the agent's answer
GET    /api/threads                       list threads for the sidebar
GET    /api/threads/{thread_id}/messages  full history of one thread (to resume it)
GET    /api/threads/{thread_id}/state     is this thread's LangGraph run interrupted?
POST   /api/threads/{thread_id}/resume    continue an interrupted run from its checkpoint
DELETE /api/threads/{thread_id}           delete a thread's history
POST   /api/documents/upload              upload a PDF and embed it into the vector DB

Design notes
------------
* `thread_id` doubles as both the JSON-memory `conversation_id`
  (src.memory.conversation.ConversationMemory) and the LangGraph checkpoint
  `thread_id` (src.agent.graph's SqliteSaver). run_agent() already accepts
  both separately, so we just pass the same value for each -> the frontend
  only ever has to track one id per conversation, which is what gets shown
  in the sidebar and sent back to resume.
* Resuming: run_agent() only ever invoked the graph with a brand-new state
  dict, so an interrupted run (e.g. a node's retries exhausted and it
  raised) could never actually be continued - the next call just started a
  new turn on top of it. /api/threads/{thread_id}/state now reports whether
  a thread stopped mid-graph, and /api/threads/{thread_id}/resume (or
  POST /api/chat with resume=true) calls run_agent(..., resume=True), which
  invokes the compiled graph with input=None so LangGraph continues from
  the exact checkpointed step instead of redoing the whole run.
* Uploads: src.rag.loader.load_markdown_documents always reads every PDF out
  of `kd_loc` (via PyPDFDirectoryLoader) rather than a single file, so the
  upload endpoint saves the new file into `kd_loc` and then re-runs the
  existing loader -> fixed_chunking -> create_embedding pipeline for the
  "kb_fixed_size" collection, which is the collection src.rag.retrieval
  actually queries. That means only PDFs are supported today, and each
  upload re-embeds the whole knowledge-base directory (same behavior
  src.rag.vector_store.build_storages() already has) rather than just the
  new file - flagged here rather than silently "fixed" since only main.py
  was asked for.
* Request logging: every /api/chat and /api/threads/{id}/resume call is
  logged as one JSON-Lines entry (trace id, thread id, duration, masked
  request/response text) via src.observability.request_logging.log_request.
  This is separate from the retry-warning logging already configured in
  src/logging_config.py / used by nodes.py's generate_response().
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator

# main.py, right after the stdlib imports
from src.observability.mlflow_tracing import setup_tracing
setup_tracing()

from src.agent.agent import get_thread_status, run_agent
from src.config import chroma_loc, conversations_file_loc, kd_loc
from src.memory.conversation import ConversationMemory
from src.observability.request_logging import log_request, new_trace_id
from src.rag.chunking import fixed_chunking
from src.rag.embeddings import create_embedding
from src.rag.loader import load_markdown_documents

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="Cartmind Agent API", version="1.0.0")

# Tighten allow_origins to your actual frontend URL before shipping this.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ConversationMemory only wraps a JSON file path (from src.config), so one
# shared instance is safe to reuse across requests.
con_memory = ConversationMemory()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: Optional[str] = Field(
        None,
        description="User's message to the agent. Not required when resume=true.",
    )
    thread_id: Optional[str] = Field(
        None,
        description="Existing thread id to resume. Omit to start a new thread.",
    )
    resume: bool = Field(
        False,
        description=(
            "If true, continue an interrupted run for thread_id from its "
            "LangGraph checkpoint instead of starting a new turn. "
            "thread_id is required when this is set."
        ),
    )

    @model_validator(mode="after")
    def _check_required_fields(self):
        if self.resume and not self.thread_id:
            raise ValueError("thread_id is required when resume=true")
        if not self.resume and not (self.message and self.message.strip()):
            raise ValueError("message is required unless resume=true")
        return self


class ChatResponse(BaseModel):
    thread_id: str
    answer: str
    resumed: bool = False
    trace_id: Optional[str] = None


class Message(BaseModel):
    role: str
    content: str


class ThreadSummary(BaseModel):
    thread_id: str
    message_count: int
    last_message: Optional[str] = None


class ThreadMessagesResponse(BaseModel):
    thread_id: str
    messages: list[Message]


class ThreadStateResponse(BaseModel):
    thread_id: str
    exists: bool
    interrupted: bool
    next_nodes: list[str]


class UploadResponse(BaseModel):
    filename: str
    chunks_indexed: int
    collection: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_conversations_store() -> dict:
    """Read the same JSON file ConversationMemory persists to, for listing."""
    if not conversations_file_loc.exists():
        return {}
    try:
        content = conversations_file_loc.read_text(encoding="utf-8")
        return json.loads(content) if content.strip() else {}
    except json.JSONDecodeError:
        return {}


def _thread_sort_key(summary: ThreadSummary):
    # Default ids from ConversationMemory.get_next_conversation_id() are
    # numeric strings ("1001", "1002", ...); sort those numerically so the
    # sidebar orders newest-first, and fall back to plain string sort for
    # any custom thread_id a client might pass in.
    try:
        return (0, int(summary.thread_id))
    except ValueError:
        return (1, summary.thread_id)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """Run one turn of the agent, creating or resuming a thread.

    Set `resume: true` (with `thread_id`) to continue a run that was
    interrupted mid-graph, instead of starting a new turn.
    """
    trace_id = new_trace_id()

    if req.resume:
        thread_id = req.thread_id
        with log_request(
            "/api/chat",
            thread_id=thread_id,
            request_text=req.message,
            trace_id=trace_id,
            extra={"resume": True},
        ) as ctx:
            try:
                answer = run_agent(
                    query=req.message or "",
                    conversation_id=thread_id,
                    con_memory=con_memory,
                    thread_id=thread_id,
                    resume=True,
                )
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Resume failed: {exc}") from exc
            ctx["response_text"] = answer

        return ChatResponse(thread_id=thread_id, answer=answer, resumed=True, trace_id=trace_id)

    thread_id = req.thread_id or con_memory.get_next_conversation_id()

    with log_request(
        "/api/chat",
        thread_id=thread_id,
        request_text=req.message,
        trace_id=trace_id,
        extra={"resume": False},
    ) as ctx:
        try:
            answer = run_agent(
                query=req.message,
                conversation_id=thread_id,
                con_memory=con_memory,
                thread_id=thread_id,
            )
        except Exception as exc:
            # LangGraph may have already checkpointed partial progress under
            # `thread_id` (e.g. classify_intent succeeded before a downstream
            # node raised). For a brand-new thread the client never had this id
            # to begin with, so a plain HTTPException here would strand it -
            # the frontend would have no thread_id to ask /state about, and the
            # resume flow could never trigger. Returning it in the body fixes
            # that.
            ctx["status"] = "error"
            ctx["error"] = f"{type(exc).__name__}: {exc}"
            return JSONResponse(
                status_code=500,
                content={
                    "detail": f"Agent failed: {exc}",
                    "thread_id": thread_id,
                    "trace_id": trace_id,
                },
            )
        ctx["response_text"] = answer

    return ChatResponse(thread_id=thread_id, answer=answer, resumed=False, trace_id=trace_id)


# ---------------------------------------------------------------------------
# Threads (sidebar + resume)
# ---------------------------------------------------------------------------

@app.get("/api/threads", response_model=list[ThreadSummary])
def list_threads() -> list[ThreadSummary]:
    """List every persisted thread, for the sidebar."""
    store = _read_conversations_store()

    summaries = [
        ThreadSummary(
            thread_id=tid,
            message_count=len(data.get("messages", [])),
            last_message=(data.get("messages") or [{}])[-1].get("content")
            if data.get("messages")
            else None,
        )
        for tid, data in store.items()
    ]

    summaries.sort(key=_thread_sort_key, reverse=True)
    return summaries


@app.get("/api/threads/{thread_id}/messages", response_model=ThreadMessagesResponse)
def get_thread_messages(thread_id: str) -> ThreadMessagesResponse:
    """Full history for one thread, so the UI can render it before resuming."""
    if not con_memory.exists(thread_id):
        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found")

    history = con_memory.get_history(thread_id)
    return ThreadMessagesResponse(
        thread_id=thread_id,
        messages=[Message(**m) for m in history],
    )


@app.get("/api/threads/{thread_id}/state", response_model=ThreadStateResponse)
def get_thread_state(thread_id: str) -> ThreadStateResponse:
    """
    Report whether this thread's LangGraph checkpoint stopped mid-run.

    `interrupted=true` means a previous /api/chat call for this thread_id
    raised partway through the graph (e.g. an LLM/tool call's retries were
    exhausted) and there's a pending node it never reached. The frontend can
    use this to show a "Resume" action instead of (or alongside) letting the
    user resend their message, which would start a brand-new turn.
    """
    status = get_thread_status(thread_id)
    return ThreadStateResponse(
        thread_id=thread_id,
        exists=status["exists"],
        interrupted=status["interrupted"],
        next_nodes=status["next_nodes"],
    )


@app.post("/api/threads/{thread_id}/resume", response_model=ChatResponse)
def resume_thread(thread_id: str) -> ChatResponse:
    """
    Continue an interrupted run for `thread_id` from its LangGraph checkpoint.

    Equivalent to POST /api/chat with {"thread_id": thread_id, "resume": true}.
    """
    trace_id = new_trace_id()

    with log_request(
        "/api/threads/{thread_id}/resume",
        thread_id=thread_id,
        request_text=None,
        trace_id=trace_id,
        extra={"resume": True},
    ) as ctx:
        try:
            answer = run_agent(
                query="",
                conversation_id=thread_id,
                con_memory=con_memory,
                thread_id=thread_id,
                resume=True,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Resume failed: {exc}") from exc
        ctx["response_text"] = answer

    return ChatResponse(thread_id=thread_id, answer=answer, resumed=True, trace_id=trace_id)


@app.delete("/api/threads/{thread_id}")
def delete_thread(thread_id: str) -> dict:
    """Delete a thread's persisted history (mirrors the CLI's 'clear')."""
    if not con_memory.exists(thread_id):
        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found")

    con_memory.clear(thread_id)
    return {"thread_id": thread_id, "deleted": True}


# ---------------------------------------------------------------------------
# Document upload -> vector DB
# ---------------------------------------------------------------------------

@app.post("/api/documents/upload", response_model=UploadResponse)
def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    """
    Upload a PDF and (re-)embed the knowledge-base directory into the
    "kb_fixed_size" Chroma collection - the one src.rag.retrieval queries.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported by the current RAG loader.",
        )

    kd_loc.mkdir(parents=True, exist_ok=True)
    destination = Path(kd_loc) / file.filename

    with destination.open("wb") as out_file:
        shutil.copyfileobj(file.file, out_file)

    try:
        documents = load_markdown_documents(kd_loc)
        chunks = fixed_chunking(documents)
        create_embedding(chunks, chroma_loc, "kb_fixed_size")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Embedding failed: {exc}") from exc

    return UploadResponse(
        filename=file.filename,
        chunks_indexed=len(chunks),
        collection="kb_fixed_size",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
