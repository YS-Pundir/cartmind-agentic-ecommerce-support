def detect_prompt_injection(text: str) -> bool:
    """Detects common prompt injection patterns using a keyword-based filter.
    Returns True if an injection is detected, False otherwise.
    """
    injection_keywords = [
        "ignore previous instructions",
        "disregard all prior instructions",
        "act as a different role",
        "you are no longer",
        "forget everything",
        "new persona",
        "system override",
        "developer mode",
        "jailbreak",
        "output in code",
        "show me the prompt",
        "what are your instructions"
    ]

    # Check for exact keyword matches (case-insensitive)
    for keyword in injection_keywords:
        if keyword in text.lower():
            return True
    return False

print("Prompt injection detection function 'detect_prompt_injection' defined.")