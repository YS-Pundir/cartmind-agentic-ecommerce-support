from langchain_core.messages import HumanMessage,AIMessage
import re

_ANAPHORA_MARKERS = {"that", "this", "it", "them", "those", "same", "also", "too"}

def _needs_history_context(query: str) -> bool:
    """Heuristic: does this query rely on something said earlier?"""
    words = set(re.findall(r"[a-z']+", query.lower()))
    return bool(words & _ANAPHORA_MARKERS)

def _recent_context(chat_history: list, max_turns: int = 2) -> str:
    """Last few USER turns only — skip the agent's own verbose answers,
    which tend to be long and dilute the embedding more than they help."""
    user_turns = [
        m.content for m in chat_history
        if isinstance(m,( HumanMessage,AIMessage))
    ][-(max_turns + 1):-1]  # exclude the current turn itself
    return " ".join(user_turns)
