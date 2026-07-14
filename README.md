# Redactive — DLP Classifier API (Step 3: Regex + NER + LLM Layers)

An LLM-powered Data Loss Prevention classifier, built in layers.
All three core guards are now wired together.

## What's here

```
app/
  main.py                 -> FastAPI app (Redactive), /analyze and /health endpoints
  config.py                -> loads ANTHROPIC_API_KEY and model name from .env
  guards/
    regex_guard.py         -> Guard 1: pattern matching for SSN, credit cards,
                               emails, phone numbers, AWS keys, generic API
                               keys, IPv4 addresses
    ner_guard.py            -> Guard 2: spaCy NER for names, orgs, locations,
                               money mentions, nationalities/groups
    llm_guard.py             -> Guard 3: Claude reviews the whole message for
                               context-dependent risk, returns a risk score,
                               a plain-English explanation, and flagged phrases
requirements.txt
.env.example
```

## Install (new for Step 3)

```bash
pip install --only-binary :all: -r requirements.txt
```

This adds `openai` (client library — used to call Groq, since Groq's API is
OpenAI-SDK-compatible) and `python-dotenv` (loads your API key from a `.env`
file) on top of everything from Steps 1-2.

## Set up your API key (Groq — free, no credit card)

1. Copy `.env.example` to a new file named `.env` in the project root
2. Get a free key at https://console.groq.com/keys (sign up with email/Google, no card needed)
3. Paste it in: `GROQ_API_KEY=gsk_...`

Groq's free tier is generous (thousands of requests/day on Llama 3.3 70B),
more than enough for building and testing this project. The code is written
so swapping to Anthropic's Claude API later only means changing the client
setup inside `llm_guard.py` — nothing else in the pipeline needs to change.

**Without a key set, the app still runs fine** — the LLM guard returns
`"enabled": false` and an explanation instead of crashing, so regex and NER
keep working on their own. This was tested deliberately so the pipeline
degrades gracefully rather than failing hard.

## Run it locally

```bash
uvicorn app.main:app --reload
```

Visit http://localhost:8000/docs and test `/analyze` with something like:

```json
{"text": "Our Q3 revenue is $4.2M, please don't share this outside the team."}
```

Notice this sentence has **no SSN, no email, no obvious pattern** — regex
and NER alone would barely flag it. The LLM layer is what catches that this
is confidential information paired with an instruction to keep it secret,
and explains why in plain English in the `llm_review` field of the response.

## How the risk score works now

`risk_score` = (sum of regex + NER severities) + (LLM's own risk_score),
capped at 100. The LLM's score is judged independently based on context,
so it can flag something as risky even when regex/NER found nothing at all.

## What's next

- Cascade logic: only call the LLM when regex/NER already found something
  borderline, to save cost and latency (right now the LLM runs on every
  request, which works but isn't optimized yet)
- Adversarial evasion test suite: systematically try to fool the classifier
  with obfuscated inputs, measure detection rate per layer
- Deploy to Render/Railway, add API key auth
- Chrome extension client
