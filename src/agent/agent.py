from __future__ import annotations
from src.agent.graph import app
import src.logging_config
from src.config import conversations_file_loc
from src.memory.conversation import ConversationMemory

MEMORY_FILE = conversations_file_loc


def print_history(history: list[dict[str, str]]) -> None:
    """Display persisted conversation history."""

    if not history:
        print("\n[Memory] No previous conversation found.")
        return

    print("\n[Memory] Previous conversation:")

    for message in history:
        role = message["role"].upper()
        content = message["content"]

        print(f"{role}: {content}")


def run_agent(
    query: str,
    conversation_id: str,
    memory: ConversationMemory,
):
    """
    Run one turn of the LangGraph agent using persisted memory.
    """

    # ---------------------------------------------------------
    # 1. Load persisted conversation history
    # ---------------------------------------------------------

    history = memory.get_history(conversation_id)

    # ---------------------------------------------------------
    # 2. Build LangGraph state
    # ---------------------------------------------------------

    state = {
        "input": query,
        "chat_history": history,
    }

    # ---------------------------------------------------------
    # 3. Run LangGraph
    # ---------------------------------------------------------

    result = app.invoke(state)

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

    memory.add_exchange(
        conversation_id=conversation_id,
        user_message=query,
        assistant_message=answer,
    )

    return answer

