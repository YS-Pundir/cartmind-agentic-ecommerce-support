# safe_parse.py — defensive JSON parse for model output

import json  # Standard JSON parser
import re  # Match markdown fences

def strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` wrappers if the model added them."""
    cleaned = text.strip()  # Trim outer whitespace
    match = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", cleaned, flags=re.IGNORECASE)
    return match.group(1).strip() if match else cleaned  # Inner JSON or original text


def extract_json_object(text: str) -> str:
    """If prose surrounds JSON, slice from first { to last }."""
    start, end = text.find("{"), text.rfind("}")  # Brace positions
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object braces found in model output.")
    return text[start : end + 1]  # Substring that should be one object


def safe_parse_model_json(raw: str) -> dict:
    """Strip fences, extract object, parse, type-check — one policy for all callers."""
    step1 = strip_markdown_fences(raw)  # Remove ``` fences
    step2 = extract_json_object(step1)  # Cut to {...} region
    try:
        data = json.loads(step2)  # String → Python values
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON parse failed: {exc}\nSnippet: {step2[:200]}") from exc
    if not isinstance(data, dict):
        raise ValueError("Top-level JSON must be an object (dict).")
    return data  # Ready for validation
