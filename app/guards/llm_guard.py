"""
Guard 3 — LLM layer.

Regex and NER catch things with a fixed shape or a recognizable entity type,
but neither understands *context*. A sentence like "our Q3 revenue is $4.2M,
don't share this outside the team" isn't dangerous because of any pattern —
it's dangerous because of what it means together. That's what this layer is
for: it reads the whole message the way a human reviewer would, and explains
its reasoning in plain English instead of just returning a label.

This is also the layer that generates the human-readable explanation used
in the final report — the "why was this flagged" text that regex and NER
can't produce on their own.

Uses Groq (free tier, OpenAI-SDK-compatible) by default. To swap to
Anthropic's Claude API later: replace the client setup below with the
`anthropic` SDK, keep the same scan_llm() signature and return shape, and
nothing else in the pipeline needs to change.
"""

import json
from openai import OpenAI
from app.config import GROQ_API_KEY, LLM_MODEL

_client = (
    OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
    if GROQ_API_KEY
    else None
)

SYSTEM_PROMPT = """You are a Data Loss Prevention (DLP) reviewer. You read a \
piece of text that a lower-level scanner has already partially checked, and \
you judge whether the text as a WHOLE contains sensitive or risky \
information that depends on context — not just isolated patterns.

Examples of context-dependent risk: confidential financial figures, \
instructions to withhold information from certain people, source code or \
credentials described in prose rather than a fixed format, health or legal \
details tied to a named person, anything that reads like an intentional or \
accidental data leak.

Respond ONLY with valid JSON, no other text, in this exact shape:
{
  "risk_score": <integer 0-100>,
  "explanation": "<one or two sentence plain-English reason>",
  "flagged_phrases": ["<short exact phrase from the text>", ...]
}

Do not repeat findings that are already unambiguous and cleanly formatted \
(a plain, correctly-formatted email address or phone number sitting in \
ordinary text) — a simple scanner already catches those reliably, so \
re-flagging them adds no value.

However — this is important — if something in the text LOOKS like it might \
be a disguised, obfuscated, or broken-up version of sensitive data (unusual \
spacing between characters, reversed text, encoded-looking strings, letters \
replaced with numbers or lookalike symbols, a value split across two parts \
of the message), you should flag it even if you cannot be fully certain \
what it decodes to. A simple pattern scanner cannot see through obfuscation \
at all, so for anything that looks deliberately disguised, you are likely \
the only layer that can catch it — treat that uncertainty as a reason to \
flag, not a reason to stay silent.

If nothing risky is present at all, return risk_score 0, a short \
explanation saying why, and an empty flagged_phrases list."""


def scan_llm(text: str) -> dict:
    """
    Sends text to the LLM for contextual review.
    Returns a dict with risk_score, explanation, and flagged_phrases.
    If no API key is configured, returns a clearly-marked disabled result
    instead of crashing — keeps the rest of the pipeline usable without it.
    """
    if _client is None:
        return {
            "risk_score": 0,
            "explanation": "LLM layer disabled — no GROQ_API_KEY configured.",
            "flagged_phrases": [],
            "source": "llm",
            "enabled": False,
        }

    response = _client.chat.completions.create(
        model=LLM_MODEL,
        max_tokens=500,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    )

    raw = response.choices[0].message.content.strip()
    # Models sometimes wrap JSON in markdown fences despite instructions —
    # strip those defensively rather than trusting the prompt alone.
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "risk_score": 0,
            "explanation": "LLM response could not be parsed as JSON.",
            "flagged_phrases": [],
            "source": "llm",
            "enabled": True,
            "error": True,
        }

    return {
        "risk_score": int(parsed.get("risk_score", 0)),
        "explanation": parsed.get("explanation", ""),
        "flagged_phrases": parsed.get("flagged_phrases", []),
        "source": "llm",
        "enabled": True,
    }