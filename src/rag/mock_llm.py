"""
src/rag/mock_llm.py — the ONE deterministic, offline LLM used everywhere MOCK_LLM=true.

Replaces your current mock_llm.py, which defines a MockLLM class that is never
imported by generation.py or nodes.py (both of those call the real Groq API
directly). This file is a genuine drop-in for `groq.Groq`: it exposes the same
`client.chat.completions.create(...)` -> `response.choices[0].message.content`
shape, so swapping it in needs a one-line change at each call site (see bottom
of this file for the exact patch).

It handles all three places your capstone needs an LLM under MOCK_LLM:
  1. Grounded RAG generation   (src/rag/generation.py)          -> extractive
     answer built ONLY from the retrieved context, never invented text.
  2. Structured ticket output  (src/agent/nodes.py generate_response) -> a
     JSON object built deterministically from intent + tool_output.
  3. RAG-triad judge           (Part 3 Task 13, new code you write) -> call
     judge_rag_triad(query, context, answer) directly, no prompt needed.

Everything here is pure string/set logic — zero network, zero API key,
zero randomness. Same input always gives the same output, which is what lets
your graded transcripts be reproducible.
"""

from __future__ import annotations

import json
import re

# ---------------------------------------------------------------------------
# Groq-shaped response wrappers, so this can be handed to code that does
# `response.choices[0].message.content` without any other change.
# ---------------------------------------------------------------------------


class _Message:
    def __init__(self, content: str):
        self.content = content


class _Choice:
    def __init__(self, content: str):
        self.message = _Message(content)


class _ChatCompletionResponse:
    def __init__(self, content: str):
        self.choices = [_Choice(content)]


class _Completions:
    def create(
        self,
        model=None,
        messages=None,
        temperature=0.0,
        max_tokens=None,
        response_format=None,
        **kwargs,
    ):
        messages = messages or []
        system_msg = next((m.get("content", "") for m in messages if m.get("role") == "system"), "")
        user_msg = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")

        wants_json = bool(response_format) and response_format.get("type") == "json_object"

        if wants_json or _looks_like_ticket_prompt(system_msg, user_msg):
            content = _generate_ticket_json(system_msg, user_msg)
        else:
            content = _generate_grounded_answer(user_msg)

        return _ChatCompletionResponse(content)


class _Chat:
    def __init__(self):
        self.completions = _Completions()


class MockGroqClient:
    """Deterministic, offline stand-in for groq.Groq — identical call surface."""

    def __init__(self, api_key=None, **kwargs):
        self.chat = _Chat()


# kept for backwards compatibility with anything that still imports `mock_llm`
mock_llm = MockGroqClient()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "to", "for", "in", "on",
    "and", "or", "what", "how", "do", "does", "did", "i", "my", "your", "you",
    "can", "will", "it", "this", "that", "be", "with", "as", "at", "by", "if",
}


def _tokenize(text: str) -> set:
    return {w for w in re.findall(r"[a-zA-Z]+", (text or "").lower()) if w not in _STOPWORDS}


def _overlap_ratio(a_tokens: set, b_tokens: set) -> float:
    if not a_tokens:
        return 0.0
    return round(len(a_tokens & b_tokens) / len(a_tokens), 4)


def _split_sentences(block: str):
    parts = re.split(r"(?<=[.!?])\s+", block or "")
    return [p.strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# 1. Grounded RAG generation
# ---------------------------------------------------------------------------
# Matches qna_user_message_template in generation.py:
#   ###Context\n{context}\n\n###Question\n{question}


def _generate_grounded_answer(user_msg: str) -> str:
    ctx_match = re.search(r"###Context\s*(.*?)###Question", user_msg, re.S)
    q_match = re.search(r"###Question\s*(.*)", user_msg, re.S)
    context_block = ctx_match.group(1).strip() if ctx_match else ""
    question = q_match.group(1).strip() if q_match else user_msg

    if not context_block:
        return "I don't know — I don't have enough information in the knowledge base to answer that."

    q_tokens = _tokenize(question)
    sentences = _split_sentences(context_block)

    scored = [(_overlap_ratio(q_tokens, _tokenize(s)), s) for s in sentences]
    scored.sort(key=lambda pair: -pair[0])

    top = [s for score, s in scored[:3] if score > 0]
    if not top:
        # Nothing in the retrieved context actually matches the question.
        # NOTE: your empirically calibrated similarity threshold (Task 4) should
        # already have stopped low-similarity queries before they reach here —
        # see the wiring note at the bottom of this file. This is a second,
        # LLM-side safety net for the same "don't invent an answer" rule.
        return "I don't know — the retrieved context doesn't contain a clear answer to that question."

    return "Based on the knowledge base: " + " ".join(top)


# ---------------------------------------------------------------------------
# 2. Structured ticket JSON (matches src/structured_output/validate_ticket.py)
# ---------------------------------------------------------------------------

_ALLOWED_ACTIONS = {
    "order_status_check",
    "policy_lookup",
    "feedback_collection",
    "human_escalation",
    "prompt_injection_detection",
    "error_handling",
}
_ALLOWED_STATUS = {"success", "not_found", "escalated", "blocked", "error", "validation_failed"}

_INTENT_TO_ACTION = {
    "policy_query": "policy_lookup",
    "order_status": "order_status_check",
    "feedback_request": "feedback_collection",
    "defer_request": "human_escalation",
    "prompt_injection": "prompt_injection_detection",
}


def _looks_like_ticket_prompt(system_msg: str, user_msg: str) -> bool:
    blob = f"{system_msg}\n{user_msg}"
    return any(k in blob for k in ("Intent:", "Tool Output:", "action_taken", "needs_human"))


def _generate_ticket_json(system_msg: str, user_msg: str) -> str:
    intent_match = re.search(r"Intent:\s*(\w+)", user_msg)
    tool_output_match = re.search(r"Tool Output:(.*?)(?:Generate the final|$)", user_msg, re.S)

    intent = intent_match.group(1).strip() if intent_match else "policy_query"
    tool_output = tool_output_match.group(1).strip() if tool_output_match else ""

    action_taken = _INTENT_TO_ACTION.get(intent, "error_handling")
    assert action_taken in _ALLOWED_ACTIONS

    lowered = tool_output.lower()
    if intent == "prompt_injection":
        status = "blocked"
    elif "error" in lowered or "sorry" in lowered or "unable" in lowered:
        status = "error"
    elif "could not extract" in lowered or "not found" in lowered:
        status = "not_found"
    elif intent == "defer_request":
        status = "escalated"
    else:
        status = "success"
    assert status in _ALLOWED_STATUS

    needs_human = status in ("escalated", "error") or intent == "defer_request"

    response_message = tool_output.strip() or "Thanks for reaching out — here is what I found for you."
    if len(response_message) < 5:
        response_message = response_message.ljust(5, ".")

    ticket = {
        "action_taken": action_taken,
        "status": status,
        "response_message": response_message,
        "needs_human": needs_human,
        # Extra fields kept for schemas/UI code (route_to_ui) that expect them.
        # Safe to ignore if your schema's "required" list doesn't ask for them —
        # check schema/agent_response.json and trim if it's stricter than this.
        "summary": response_message[:60],
        "priority": "high" if needs_human else "normal",
        "category": intent,
        "suggested_reply": response_message,
    }
    return json.dumps(ticket)


# ---------------------------------------------------------------------------
# 3. RAG-triad judge (Part 3, Task 13) — call this directly, no prompt needed
# ---------------------------------------------------------------------------


def judge_rag_triad(query: str, context: str, answer: str) -> dict:
    """Deterministic stand-in for an LLM-as-judge under MOCK_LLM.

    Each score is in [0, 1], derived from content-word overlap:
      - context_relevance: how much of the query's meaning shows up in the
        retrieved context (does retrieval fetch the right thing?)
      - groundedness:       how much of the answer's content is actually
        present in the context (did generation invent anything?)
      - answer_relevance:   how much of the query's meaning shows up in the
        answer (did generation actually address the question?)

    "I don't know" answers naturally score low on groundedness/answer_relevance
    here, since they share almost no content words with the context or query —
    which is the correct judge behaviour for a refused, out-of-scope query.
    """
    q_tokens = _tokenize(query)
    c_tokens = _tokenize(context)
    a_tokens = _tokenize(answer)

    return {
        "context_relevance": _overlap_ratio(q_tokens, c_tokens),
        "groundedness": _overlap_ratio(a_tokens, c_tokens),
        "answer_relevance": _overlap_ratio(q_tokens, a_tokens),
    }


if __name__ == "__main__":
    # Smoke test — run `python -m src.rag.mock_llm`
    client = MockGroqClient()

    grounded_prompt = [
        {"role": "system", "content": "Answer using only the provided context."},
        {
            "role": "user",
            "content": (
                "###Context\n"
                "Items in the Apparel category can be returned within 30 days of delivery. "
                "Footwear has a 15-day return window due to hygiene considerations.\n"
                "###Question\nWhat is the return window for apparel?"
            ),
        },
    ]
    print("[grounded]", client.chat.completions.create(messages=grounded_prompt).choices[0].message.content)

    ticket_prompt = [
        {"role": "system", "content": "Respond with the required JSON structure."},
        {
            "role": "user",
            "content": "Intent:order_status\n\nTool Output:{'status': 'Shipped', 'escalation_score': 0.2}\n\nGenerate the final customer-support response using the required JSON structure.",
        },
    ]
    print(
        "[ticket]",
        client.chat.completions.create(
            messages=ticket_prompt, response_format={"type": "json_object"}
        ).choices[0].message.content,
    )

    print(
        "[judge]",
        judge_rag_triad(
            query="What is the return window for apparel?",
            context="Items in the Apparel category can be returned within 30 days of delivery.",
            answer="Based on the knowledge base: Items in the Apparel category can be returned within 30 days of delivery.",
        ),
    )
