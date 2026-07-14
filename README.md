# Redactive — DLP Classifier API (Step 4: Combine + Redact)

An LLM-powered Data Loss Prevention classifier, built in layers.
Findings from all three guards now get merged, deduplicated, and used to
produce a redacted version of the input text — not just a list of what's risky.

## What's here

```
app/
  main.py                 -> FastAPI app (Redactive), /analyze and /health
  config.py                -> loads GROQ_API_KEY and model name from .env
  models/
    schemas.py              -> shared request/response models
  guards/
    regex_guard.py          -> Guard 1: pattern matching (SSN, credit cards,
                                emails, phone numbers, AWS keys, IPv4, etc.)
    ner_guard.py             -> Guard 2: spaCy NER (names, orgs, locations,
                                money mentions, nationalities/groups)
    llm_guard.py              -> Guard 3: Groq LLM contextual review — risk
                                score, plain-English explanation, flagged phrases
  pipeline/
    combine.py                 -> merges + deduplicates findings across guards
  redaction/
    redactor.py                  -> builds a redacted version of the text
requirements.txt
.env.example
```

## Install

No new dependencies for Step 4 — same install as Step 3:

```bash
pip install --only-binary :all: -r requirements.txt
```

## Set up your API key (Groq — free, no credit card)

1. Copy `.env.example` to a new file named `.env` in the project root
2. Get a free key at https://console.groq.com/keys
3. Paste it in: `GROQ_API_KEY=gsk_...`

**Without a key set, the app still runs fine** — the LLM guard returns
`"enabled": false` and an explanation instead of crashing, so regex + NER
+ redaction keep working on their own.

## Run it locally

```bash
python -m uvicorn app.main:app --reload
```

Visit http://localhost:8000/docs and test `/analyze`:

```json
{"text": "My SSN is 123-45-6789 and I work with Rohan Mehta at Skyhigh Security."}
```

## What's new in Step 4

The response now includes `redacted_text` — a safe version of the input
with every flagged span replaced by a labeled placeholder:

```json
{
  "original_text": "My SSN is 123-45-6789 and I work with Rohan Mehta at Skyhigh Security.",
  "redacted_text": "My [REDACTED_ORG] is [REDACTED_SSN] and I work with [REDACTED_PERSON] at [REDACTED_ORG].",
  "findings": [...],
  "risk_score": 75,
  "layers_used": ["regex", "ner", "llm"],
  "llm_review": {...}
}
```

Two things worth understanding about how this works:

- **`combine.py`** deduplicates overlapping findings from different guards
  (e.g. if regex and NER both flag overlapping spans, the higher-severity
  finding wins and the other is dropped) before anything gets redacted.
- **`redactor.py`** replaces spans starting from the end of the string
  backward, so earlier replacements don't shift the character positions
  of findings still waiting to be redacted.

**Known limitation worth knowing about:** you may notice the word "SSN"
itself sometimes gets misread by the NER model as an organization name
(`ner_org`) and gets redacted too, producing slightly odd output like
`"My [REDACTED_ORG] is [REDACTED_SSN]..."`. This is a real spaCy false
positive, not a bug in the redaction logic — and it's a good concrete
example to have on hand when you build the evasion/false-positive report
in a later step.

## What's next

- Cascade logic: only call the LLM when regex/NER already found something
  borderline, to save cost and latency
- Adversarial evasion test suite: systematically try to fool the classifier
  with obfuscated inputs, measure detection rate per layer
- Deploy to Render/Railway, add API key auth
- Chrome extension client
