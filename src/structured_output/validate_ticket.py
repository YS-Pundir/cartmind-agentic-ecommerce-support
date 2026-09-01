# validate_ticket.py — hand-written checks against schema (no extra library)

from typing import Tuple

ALLOWED_ACTIONS = {
        "order_status_check",
        "policy_lookup",
        "feedback_collection",
        "human_escalation",
        "prompt_injection_detection",
        "error_handling"
      }
ALLOWED_STATUS = {
        "success",
        "not_found",
        "escalated",
        "blocked",
        "error",
        "validation_failed"
      }


def validate_ticket(data: dict, schema: dict) -> Tuple[bool, str]:
    """Return (True, 'ok') or (False, reason) on first failure."""
    for key in schema.get("required", []):
        if key not in data:
            return False, f"Missing required field: {key}"
    if data["action_taken"] not in ALLOWED_ACTIONS:
        return False, f"Invalid category: {data["action_taken"]!r}"

    
    if data["status"] not in ALLOWED_STATUS:
        return False, f"Invalid priority: {data['status']!r}"

    
    if not isinstance(data["response_message"], str) or len(data["response_message"].strip()) < 5:
        return False, "response_message must be a non-empty string (min 5 chars)."

    
    if not isinstance(data["needs_human"], bool):
        return False, "needs_human must be boolean."
    return True, "ok"


def validate_or_raise(data: dict, schema: dict) -> dict:
    """Raise ValueError on failure — uniform error handling for callers."""
    ok, message = validate_ticket(data, schema)
    if not ok:
        raise ValueError(message)
    return data


def route_to_ui(ticket: dict) -> dict:
    """Map validated dict to UI props — frontend never parses raw model text."""
    return {
        "title": ticket["summary"],
        "badge": ticket["priority"].upper(),
        "team": ticket["category"],
        "show_draft": not ticket["needs_human"],
        "draft_text": ticket["suggested_reply"],
    }
