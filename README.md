# Redactive

**An LLM-powered Data Loss Prevention (DLP) system** — a three-layer
detection API (regex + NER + LLM), validated against a self-built
adversarial evasion suite, deployed live, and wired into a Chrome
extension that warns you before you paste sensitive data anywhere on
the web.

🔗 **Live API:** https://redactive.onrender.com
 **Interactive docs:** https://redactive.onrender.com/docs
 **Full architecture + findings:** [ARCHITECTURE.md](./ARCHITECTURE.md)
📊 **Evasion test results:** [evasion_tests/report/evasion_report.md](./evasion_tests/report/evasion_report.md)

> First request after inactivity may take 30-60s — deployed on Render's
> free tier, which spins down idle instances. Every request after that is
> fast.

---

## What it does

Send it text, it tells you what's sensitive, why, and gives you back a
redacted-safe version:

```bash
curl -X POST https://redactive.onrender.com/analyze \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key-here" \
  -d '{"text": "My SSN is 123-45-6789, please keep this confidential."}'
```

```json
{
  "redacted_text": "My [REDACTED_SSN], please keep this confidential.",
  "risk_score": 100,
  "llm_review": {
    "explanation": "Contains a Social Security Number paired with an explicit confidentiality instruction."
  }
}
```

## Headline result

**94% detection rate** against an adversarial test suite of 10 obfuscation
techniques (leetspeak, spacing, base64, reversal, zero-width injection,
homoglyphs, and more) — up from a 62.5% baseline using pattern-matching
alone. Full investigation, including two disproven hypotheses and the
actual root causes, in [ARCHITECTURE.md](./ARCHITECTURE.md).

## Architecture

```
Text ─▶ Regex ─▶ NER ─▶ Cascade decision ─▶ LLM (Groq) ─▶ Combine ─▶ Redact
                              │
                    skips LLM only when
                    nothing regex/NER
                    found AND no risk
                    language present
```

Three layers because each catches what the others structurally can't:
- **Regex** — fast, cheap, catches fixed-format data (SSNs, cards, keys)
- **NER** (spaCy) — catches free-form entities with no fixed pattern
- **LLM** (Groq, Llama 3.3 70B) — the only layer with real judgment;
  catches purely contextual risk ("our revenue is $4.2M, don't share this")

## Repo structure

```
app/
  guards/       regex_guard.py, ner_guard.py, llm_guard.py
  pipeline/      combine.py, cascade.py
  redaction/      redactor.py
  auth/            api_key.py — X-API-Key auth + rate limiting
  models/           schemas.py
  main.py, config.py

evasion_tests/    adversarial test suite + generated report
extension/        Chrome extension (Manifest V3)
Dockerfile         for Render/Railway deployment
```

## Run it locally

```bash
pip install --only-binary :all: -r requirements.txt
python -m spacy download en_core_web_sm
cp .env.example .env   # add your GROQ_API_KEY (free at console.groq.com/keys)
python -m uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` to try it. Without a `GROQ_API_KEY` set,
the app still runs — the LLM guard reports itself disabled and regex/NER
keep working on their own.

## Run the evasion suite yourself

```bash
python -m evasion_tests.run_evasion_suite
python -m evasion_tests.generate_report
```

Regenerates `evasion_tests/report/evasion_report.md` against your local
server — useful after changing any guard's logic to confirm nothing
regressed (this is exactly how a real cascade-logic regression was caught
during development — see ARCHITECTURE.md, section 4).

## Install the Chrome extension

1. Go to `chrome://extensions`, enable **Developer mode**
2. Click **Load unpacked**, select the `extension/` folder
3. Click the extension icon, paste your Redactive API key, save
4. Type sensitive-looking text into any webpage's text field — a warning
   banner appears if it's flagged

Works on any web-based text field (Gmail, Slack web, ChatGPT, Notion,
Google Docs). Doesn't work in native desktop apps (Word, Outlook desktop)
— a hard platform boundary for browser extensions, not a bug.

## Security

- Every `/analyze` call requires a valid `X-API-Key` header
- Rate limited: 30 requests / 60 seconds per key
- Secrets are never committed — `.env` is gitignored; production keys are
  set directly as environment variables on Render

## What's deliberately not built

Policy-as-code, an admin dashboard, and a feedback loop were all
considered early and deprioritized in favor of going deep on evasion
testing and cascade logic instead — see [ARCHITECTURE.md, section 7](./ARCHITECTURE.md#7-whats-deliberately-not-built-and-why)
for the full reasoning.