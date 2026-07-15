"""
Central config loading. Keeps API keys and settings out of guard files —
each guard imports what it needs from here instead of reading env vars
directly, so there's one place to check when something's misconfigured.

Using Groq (free tier, no credit card) for the LLM guard by default.
Groq's API is OpenAI-SDK-compatible, so llm_guard.py talks to it via the
`openai` package pointed at Groq's base URL. Swapping to Anthropic's API
later only requires changing llm_guard.py's client setup — the rest of
the pipeline (main.py, other guards) doesn't need to change at all.
"""

import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# The key clients must send in the X-API-Key header to use /analyze.
# If left empty, auth is effectively disabled (useful for local dev) —
# but a warning is logged so this is never accidentally left open in
# production.
REDACTIVE_API_KEY = os.getenv("REDACTIVE_API_KEY", "")

# Model used for the LLM guard layer. Kept as a config value, not
# hardcoded in llm_guard.py, so it's a one-line change to swap models.
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")