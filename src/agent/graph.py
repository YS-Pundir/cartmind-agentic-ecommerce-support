from src.agent.state import AgentState
from src.agent.nodes import (classify_intent,
                             call_defer_human_tool,
                             call_feedback_tool,
                             call_rag_tool,
                             call_sql_tool,
                             generate_response
                             )


from langchain_core.tools import tool
from langgraph.graph import END, StateGraph, START
# --- Build the LangGraph ---

workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("classify_intent", classify_intent)
workflow.add_node("call_sql_tool", call_sql_tool)
workflow.add_node("call_rag_tool", call_rag_tool)
workflow.add_node("call_feedback_tool", call_feedback_tool) # New node
workflow.add_node("call_defer_human_tool", call_defer_human_tool) # New node
workflow.add_node("generate_response", generate_response)

# Set entry point
workflow.set_entry_point("classify_intent")

# Add conditional edges
workflow.add_conditional_edges(
    "classify_intent",
    lambda state: state["intent"],
    {
        "order_status": "call_sql_tool",
        "policy_query": "call_rag_tool",
        "feedback_request": "call_feedback_tool", # New edge
        "defer_request": "call_defer_human_tool", # New edge
        "prompt_injection": "generate_response" # Direct to response for injection
    },
)

# Add edges from tool calls to response generation
workflow.add_edge("call_sql_tool", "generate_response")
workflow.add_edge("call_rag_tool", "generate_response")
workflow.add_edge("call_feedback_tool", "generate_response") # New edge
workflow.add_edge("call_defer_human_tool", "generate_response") # New edge

# Add edge from response generation to END
workflow.add_edge("generate_response", END)

# Compile the graph
app = workflow.compile()

print("LangGraph agent workflow compiled successfully with Structured Output Schema, PII Masking, and Prompt Injection Detection!")
