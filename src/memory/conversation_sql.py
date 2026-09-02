
from langchain_core.messages import HumanMessage,AIMessage

def _to_messages(raw_history: list[dict]) -> list:
    """Convert persisted {'role','content'} dicts into LangChain messages."""
    out = []
    for m in raw_history:
        if isinstance(m, dict):
            out.append(HumanMessage(content=m["content"]) if m["role"] == "user"
                        else AIMessage(content=m["content"]))
        else:
            out.append(m)  # already a BaseMessage
    return out

