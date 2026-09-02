from src.agent.state import AgentState
from src.agent.nodes import (classify_intent,
                             call_defer_human_tool,
                             call_feedback_tool,
                             call_rag_tool,
                             call_sql_tool,
                             generate_response
                             )

import time
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph, START
from src.config import checkpoint_conn_loc
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import RetryPolicy
conn = sqlite3.connect(checkpoint_conn_loc,
                       check_same_thread=False)
memory = SqliteSaver(conn)


# --- Build the LangGraph ---

def build_workflow(memory):
        

        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("classify_intent", classify_intent,retry_policy=RetryPolicy(
                max_attempts=3,
                max_interval=6,
                backoff_factor=2,
                initial_interval=0.2,
                jitter=False))
        workflow.add_node("call_sql_tool", call_sql_tool,retry_policy=RetryPolicy(
                max_attempts=3,
                max_interval=6,
                backoff_factor=2,
                initial_interval=0.2,
                jitter=False))
        workflow.add_node("call_rag_tool", call_rag_tool,retry_policy=RetryPolicy(
                max_attempts=3,
                max_interval=6,
                backoff_factor=2,
                initial_interval=0.2,
                jitter=False))
        workflow.add_node("call_feedback_tool", call_feedback_tool,retry_policy=RetryPolicy(
                max_attempts=3,
                max_interval=6,
                backoff_factor=2,
                initial_interval=0.2,
                jitter=False)) # New node
        workflow.add_node("call_defer_human_tool", call_defer_human_tool,retry_policy=RetryPolicy(
                max_attempts=3,
                max_interval=6,
                backoff_factor=2,
                initial_interval=0.2,
                jitter=False)) # New node
        workflow.add_node("generate_response", generate_response,retry_policy=RetryPolicy(
                max_attempts=3,
                max_interval=6,
                backoff_factor=2,
                initial_interval=0.2,
                jitter=False))

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
        app = workflow.compile(checkpointer=memory)

        return app

print("LangGraph agent workflow compiled successfully with Structured Output Schema, PII Masking, and Prompt Injection Detection!")
