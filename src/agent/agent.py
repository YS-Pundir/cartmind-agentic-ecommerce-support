from __future__ import annotations
from src.agent.graph import build_workflow
import src.logging_config
from src.config import conversations_file_loc
from src.memory.conversation import ConversationMemory
from src.agent.graph import memory
from src.resilience.timeouts import invoke_with_global_timeout
from concurrent.futures import TimeoutError as FutureTimeoutError

MEMORY_FILE = conversations_file_loc




def run_agent(
    query: str,
    conversation_id: str,
    con_memory: ConversationMemory,
    thread_id:str
):
    """
    Run one turn of the LangGraph agent using persisted memory.
    """

    # ---------------------------------------------------------
    # 1. Load persisted conversation history
    # ---------------------------------------------------------

    history = con_memory.get_history(conversation_id)

    # ---------------------------------------------------------
    # 2. Build LangGraph state
    # ---------------------------------------------------------

    state = {
        "input": query,
        "chat_history": history,
    }

    config = { "configurable": { "thread_id": thread_id, } }

    # ---------------------------------------------------------
    # 3. Run LangGraph
    # ---------------------------------------------------------
    try:
        app = build_workflow(memory)
        result=invoke_with_global_timeout(app,state,config,40)
    except FutureTimeoutError:
        result={"tool_output":"Sorry workflow took to much time , please try again later"}


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

