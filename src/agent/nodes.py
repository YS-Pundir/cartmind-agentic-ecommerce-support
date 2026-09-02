from src.agent.state import AgentState
import time
from src.tools.sql_tool import check_order_status
from src.tools.feedback_tool import register_feedback
from src.tools.deffered_tool import defer_to_human
from src.tools.rag_tool import rag,rag_with_score

from src.memory.conversation_sql import _to_messages
from src.memory.conversation_rag import _needs_history_context,_recent_context
from src.guardrails.injection import detect_prompt_injection
from src.guardrails.pii import mask_pii
from langchain_core.messages import HumanMessage,AIMessage
from langgraph.types import RetryPolicy
from src.resilience.timeouts import run_with_timeout
from concurrent.futures import ThreadPoolExecutor,TimeoutError as FutureTimeoutError
from src.config import (api_key,
                        resp_gen_max_token,
                        resp_gen_prompt,
                        resp_gen_model,
                        resp_gen_schema,
                        resp_gen_temp)

from src.structured_output.safe_parse import safe_parse_model_json
from src.structured_output.validate_ticket import validate_or_raise
import os
import re
import json
from groq import Groq



# For Api Rate limiting
import logging
from tenacity import (
     retry,  # Decorator that wraps a function with retry logic
    stop_after_attempt,  # Stop after N total attempts
    wait_exponential,  # Wait 1s, 2s, 4s, 8s between retries
    before_sleep_log, 

)

logger = logging.getLogger("response_generation")

attempt_counter = {"n": 0}







def classify_intent(state: AgentState) -> dict:
    """Classifies the user's intent and records the input in chat_history.
    Applies PII masking to the user input and detects prompt injection before further processing.
    """
    original_user_input = state["input"]

    # 1. Prompt Injection Detection (Pre-PII Masking to catch raw malicious input)
    if detect_prompt_injection(original_user_input):
        print("\n--- Prompt Injection Detected! ---")
        # Immediately return a response indicating injection and bypass other nodes
        return {
            "intent": "prompt_injection",
            "chat_history": state.get("chat_history", []) + [HumanMessage(content=original_user_input)],
            "tool_output": "I cannot process this request as it appears to be a prompt injection attempt. Please refrain from using malicious inputs."
        }

    # 2. Apply PII masking
    user_input = mask_pii(original_user_input)


    # normalize + copy instead of mutating in place
    chat_history = _to_messages(state.get("chat_history", []))
    chat_history = chat_history + [HumanMessage(content=user_input)]

    user_query_lower = user_input.lower()
    if "feedback" in user_query_lower or "rating" in user_query_lower or "experience" in user_query_lower:
        print("\n--- Classified Intent: feedback_request ---")
        return {"intent": "feedback_request", "chat_history": chat_history,"input":user_input}
    elif "human" in user_query_lower or "agent" in user_query_lower or "escalate" in user_query_lower or "help me further" in user_query_lower:
        print("\n--- Classified Intent: defer_request ---")
        return {"intent": "defer_request", "chat_history": chat_history,"input":user_input}
    elif "order" in user_query_lower or "record_id" in user_query_lower or "status" in user_query_lower:
        print("\n--- Classified Intent: order_status ---")
        return {"intent": "order_status", "chat_history": chat_history,"input":user_input}

    else:
        print("\n--- Classified Intent: policy_query ---")
        return {"intent": "policy_query", "chat_history": chat_history,"input":user_input}







def call_sql_tool(state: AgentState) -> dict:

    """Calls the check_order_status tool with the extracted record_id."""
    user_query = state["input"]
    # Simple regex to extract record_id, assuming format like 'ORD-XXXX'
    match = re.search(r"ORD\d{4}", user_query.upper())
    record_id = match.group(0) if match else None

    if not record_id:
        for msg in reversed(state.get("chat_history", [])):
            content = getattr(msg, "content", "")
            m = re.search(r"ORD\d{4}", content.upper())
            if m:
                record_id = m.group(0)
                break

    if record_id:
        print(f"\n--- Calling check_order_status for {record_id} ---")
        output = check_order_status(record_id)
        return {"tool_output": str(output)}
    else:
        return {"tool_output": "Could not extract a valid order ID from your query. Please provide it in the format ORD-XXXX."}




def call_rag_tool(state: AgentState) -> dict:
    """Calls the RAG tool. Falls back to history-augmented retrieval only
    when the current query looks anaphoric AND that augmentation actually
    improves retrieval confidence over the raw query."""
  
    user_query = state["input"]
    chat_history = state.get("chat_history", [])

    if not _needs_history_context(user_query):
        print(f"\n--- Calling RAG tool for '{user_query}' (no history needed) ---")
        try : 
            response= run_with_timeout(lambda:rag(user_query),10)
            return {"tool_output": response}
        except FutureTimeoutError:
            return {"tool_output": "rag genration taking too long "}

    context = _recent_context(chat_history)
    enriched_query = f"{context} {user_query}".strip() if context else user_query
    print(f"---calling rag tool with enriched query----")

    # Retrieve with both versions, keep whichever the retriever is
    # more confident about (reuses your Task-4 similarity signal).
    try : 
        enriched_result= run_with_timeout(lambda:rag(enriched_query),10)
        return {"tool_output": enriched_result}
    except FutureTimeoutError:
            return {"tool_output": "rag genration with enriched query taking too long "}

  




def call_feedback_tool(state: AgentState) -> dict:
    """Calls the feedback tool to collect user feedback."""
    
    user_query = state["input"]
    intent=state["intent"]

    print(f"\n--- Calling Feedback Tool for: '{user_query}' ---")
    # Assuming the entire input is the feedback for simplicity in this demo
    feedback = user_query.replace("give feedback", "").replace("my feedback is", "").strip()
    output = register_feedback(intent,feedback)
    return {"tool_output": output}





def call_defer_human_tool(state: AgentState) -> dict:
    """Calls the defer human tool to escalate the query."""
    user_query = state["input"]
    intent=state["intent"]

    print(f"\n--- Calling Defer Human Tool for: '{user_query}' ---")
    output = defer_to_human(user_query,intent)
    return {"tool_output": output}





@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1,min=1,max=10),
    before_sleep=before_sleep_log(logger,logging.WARNING)
)
def generate_response(state: AgentState) -> dict:
    """Call model, parse JSON, validate — return trusted dict or raise ValueError."""

    client = Groq(api_key=api_key)  # Key from env, never hard-coded

    intent=state["intent"]
    tool_output=state["tool_output"]
    history_snippet = "\n".join(
        f"{'User' if isinstance(m, HumanMessage) else 'Agent'}: {m.content}"
        for m in state.get("chat_history", [])[-6:]  # last 3 exchanges
    )

    user_message = f"""
    Recent conversation:{history_snippet}
    Intent:{intent}
    
    Tool Output:{tool_output}

    Generate the final customer-support response using the required JSON structure."""
    try:
        logger.info("RESPONSE API CALL")
        response = client.chat.completions.create(
            model=resp_gen_model,  # Fixed model for consistent output during testing
            messages=[
                {"role": "system", "content": resp_gen_prompt},  # JSON contract + behaviour rules
                {"role": "user", "content":user_message},  # Raw customer message to classify
                ],
            temperature=resp_gen_temp,  # Low randomness for stable classification
            max_tokens=resp_gen_max_token,  # Enough room for JSON object
            response_format={"type": "json_object"},  # Groq JSON syntax mode
            )
        logger.info("RESPONSE API SUCCESS")
    except Exception as e:
        logger.error(f"RESPONSE API FAILED: {e}")
        raise

    raw = response.choices[0].message.content  # Untrusted string until parsed + validated
    parsed = safe_parse_model_json(raw)  # dict or ValueError
    return validate_or_raise(parsed, resp_gen_schema)  