"""
Instruction for viewers :

Nothing else about the call site changes: `client.chat.completions.create(...)`
and `response.choices[0].message.content` work identically either way.

MOCK_LLM defaults to "true" so the project runs offline out of the box, per
the brief. Set MOCK_LLM=false (and a real api_key) only if you optionally
want to wire in a real model behind the flag.
"""

import os

from src.rag.mock_llm import MockGroqClient


def get_llm_client():
    use_mock = os.getenv("MOCK_LLM", "false").strip().lower() not in ("false", "0", "no")

    if use_mock:
        return MockGroqClient()

    # Only reached when a student explicitly opts out of MOCK_LLM.
    from groq import Groq
    from src.config import api_key

    if not api_key:
        raise RuntimeError(
            "MOCK_LLM=false but no api_key is set. Either set MOCK_LLM=true "
            "(default) or provide a real Groq api_key in your .env."
        )
    return Groq(api_key=api_key)
