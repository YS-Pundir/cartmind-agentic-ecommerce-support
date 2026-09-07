from __future__ import annotations
from src.agent.graph import build_workflow
import src.logging_config
from src.config import conversations_file_loc
from src.memory.conversation import ConversationMemory
from src.memory.conversation_sql import _to_messages
from src.agent.graph import memory
from src.resilience.timeouts import invoke_with_global_timeout
from concurrent.futures import TimeoutError as FutureTimeoutError

MEMORY_FILE = conversations_file_loc


def get_thread_status(thread_id: str) -> dict:
    """
    Inspect the LangGraph checkpoint for a thread without running anything.

    Returns:
        {
            "exists": bool,          # is there any checkpoint at all for this thread?
            "interrupted": bool,     # did the last run stop before reaching END?
            "next_nodes": list[str], # node(s) that would run next if resumed
        }
    """
    app = build_workflow(memory)
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = app.get_state(config)

    next_nodes = list(snapshot.next) if snapshot else []
    exists = bool(snapshot.values) if snapshot else False

    return {
        "exists": exists,
        "interrupted": bool(next_nodes),
        "next_nodes": next_nodes,
    }


def run_agent(
    query: str,
    thread_id: str,
    con_memory: ConversationMemory,
    conversation_id: str,
    resume: bool = False,
):
    """
    Run one turn of the LangGraph agent using persisted memory.

    If `resume=True`, this does NOT start a new turn. Instead it checks the
    LangGraph checkpoint for `thread_id`; if the previous run was interrupted
    partway through the graph (e.g. a node's retries were exhausted and it
    raised), it continues execution from exactly that point using the state
    already saved in the checkpoint - it does not re-run the nodes that
    already completed, and it does not need the original query again.
    """

    app = build_workflow(memory)
    config = {"configurable": {"thread_id": thread_id}}

    # ---------------------------------------------------------
    # Resume path: continue an interrupted checkpoint in-place
    # ---------------------------------------------------------
    if resume:
        snapshot = app.get_state(config)
        interrupted = bool(snapshot.next)

        if not interrupted:
            # Nothing pending for this thread. If the caller also gave us a
            # fresh query, just fall through and treat it as a normal new
            # turn instead of silently doing nothing.
            if not query:
                last_answer = (snapshot.values or {}).get("tool_output")
                return last_answer or "There is no interrupted run to resume for this thread."
        else:
            print(
                f"\n[Resume] Thread '{thread_id}' stopped before node(s) "
                f"{snapshot.next}. Continuing from the saved checkpoint "
                f"(no state is rebuilt from scratch)."
            )
            try:
                # Passing None as input is what tells LangGraph "don't start
                # a new turn, continue this thread_id's existing checkpoint".
                result = invoke_with_global_timeout(app, None, config, 40)
            except FutureTimeoutError:
                result = {
                    "tool_output": "Sorry workflow took to much time , please try again later"
                }

            answer = result.get("tool_output") or "I was unable to generate a response."

            # The original user turn was captured into the checkpoint's
            # chat_history before it failed, but never made it into the
            # JSON conversation log (add_exchange only ran at the end of
            # the original, failed call). Record it now so history/sidebar
            # stays consistent.
            resumed_state = app.get_state(config).values or {}
            original_query = resumed_state.get("input", query)
            con_memory.add_exchange(
                conversation_id=conversation_id,
                user_message=original_query,
                assistant_message=answer,
            )
            return answer

    # ---------------------------------------------------------
    # 1. Load persisted conversation history
    # ---------------------------------------------------------

    history = con_memory.get_history(conversation_id)

    if history:
        print(
            f"\n[Memory] Loaded {len(history)} ")
    else:
        print("\n[Memory] Fresh conversation.")

    chat_history = _to_messages(history)

    # ---------------------------------------------------------
    # 2. Build LangGraph state
    # ---------------------------------------------------------

    state = {
        "input": query,
        "chat_history": chat_history,}

    # ---------------------------------------------------------
    # 3. Run LangGraph
    # ---------------------------------------------------------
    try:
        result = invoke_with_global_timeout(app, state, config, 40)
    except FutureTimeoutError:
        result = {"tool_output": "Sorry workflow took to much time , please try again later"}


    # ---------------------------------------------------------
    # 4. Extract response
    # ---------------------------------------------------------

    # Adjust these fields if your existing graph uses
    # a different output field.

    answer = result.get("tool_output")

 
    if not answer:
        answer = "I was unable to generate a response."

    # ---------------------------------------------------------
    # 5. Persist the new exchange
    # ---------------------------------------------------------

    
    con_memory.add_exchange(
        conversation_id=conversation_id,
        user_message=query,
        assistant_message=answer,
    )

    return answer
