from typing import TypedDict
from langchain_core.messages import BaseMessage

# Define the agent state
class AgentState(TypedDict):
    record_id:str
    input: str
    chat_history: list[BaseMessage]
    tool_output: str
    intent: str # To store the classified intent
