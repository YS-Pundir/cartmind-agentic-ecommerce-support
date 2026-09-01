import re
def mask_pii(text: str) -> str:
    """
    Masks fixed-format PII fields from user input text before it reaches 
    the model or logs. Specifically targets:
      1. Phone numbers (e.g., +91-9876543210, 10-digit numbers)
      2. Payment card indicators / last-4 digits (e.g., card ending in 1234, 16-digit cards)
    """
    if not isinstance(text, str):
        return text

    # Pattern 1: Mask standard 10-digit phone numbers (with optional country code +91 or dashes/spaces)
    phone_pattern = r'(?:\+91[\-\s]?)?[6-9]\d{9}|\b\d{3}[\-\s]?\d{3}[\-\s]?\d{4}\b'
    text = re.sub(phone_pattern, "[PHONE_MASKED]", text)

    # Pattern 2: Mask 16-digit credit/debit card numbers
    card_pattern = r'\b(?:\d{4}[-\s]?){3}\d{4}\b'
    text = re.sub(card_pattern, "[CARD_MASKED]", text)

    # Pattern 3: Mask specific phrases referencing payment card last-4-digits (e.g., "ending in 1234")
    last_four_pattern = r'(?:card|ending\s+in|ending|last\s+4)\D*(\d{4})\b'
    text = re.sub(last_four_pattern, r"[CARD_LAST4_MASKED]", text, flags=re.IGNORECASE)

    return text