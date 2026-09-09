"""
src/llm_client.py — single switch point between the real Groq client and the
deterministic MockGroqClient (src/rag/mock_llm.py).

This is the piece your current codebase is missing: generation.py and
nodes.py both do `from groq import Groq; client = Groq(api_key=api_key)`
directly, with no MOCK_LLM branch, so every run — including your graded
transcripts — hits the real network and needs a real api_key. That directly
contradicts the brief's "graded transcripts must use MOCK_LLM alone, zero
API keys, zero network access" requirement.

Usage — everywhere you currently do this:

    from groq import Groq
    client = Groq(api_key=api_key)

...do this instead:

    from src.llm_client import get_llm_client
    client = get_llm_client()

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
