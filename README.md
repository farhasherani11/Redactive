# Redactive — DLP Classifier API (Step 2: Regex + NER Layers)

An LLM-powered Data Loss Prevention classifier, built in layers.
This is Step 2: regex + NER layers. LLM layer gets added next.

## What's here

```
app/
  main.py                 -> FastAPI app (Redactive), /analyze and /health endpoints
  guards/
    regex_guard.py         -> Guard 1: pattern matching for SSN, credit cards,
                               emails, phone numbers, AWS keys, generic API
                               keys, IPv4 addresses
    ner_guard.py            -> Guard 2: spaCy NER for names, orgs, locations,
                               money mentions, nationalities/groups — things
                               with no fixed pattern, only recognizable by context
requirements.txt
```

## Run it locally

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn app.main:app --reload
```

Then visit http://localhost:8000/docs for the interactive Swagger UI,
or test directly:

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "Call Rohan Mehta at 555-987-6543, he works at Skyhigh Security."}'
```

The response now includes findings from both layers — the phone number from
regex, the person's name and company from NER — merged into one report.

## How the risk score works

Each finding type has a severity weight. Regex findings (SSN, API keys) are
weighted higher since they're unambiguous and high-stakes. NER findings are
weighted lower individually since a name or company alone isn't necessarily
sensitive — but they add up, and combinations (a name + a location + an org
in the same message) push the score up meaningfully. This will get smarter
once Guard 3 (LLM) is added — the LLM can judge whether the *combination*
of entities in context is actually risky, not just their presence.

## What's next

- Guard 3: LLM layer for context-aware judgment + human-readable explanations
- Cascade logic: only call the LLM when regex/NER already found something
  borderline, to save cost and latency
- Adversarial evasion test suite: systematically try to fool the classifier
  with obfuscated inputs, measure detection rate per layer
- Deploy to Render/Railway, add API key auth
- Chrome extension client
