# Redactive — Architecture & Project Summary

**An LLM-powered Data Loss Prevention (DLP) system**: a three-layer detection
API, deployed and live, with a Chrome extension that warns users in real
time before they paste or type sensitive data anywhere on the web.

**Live API:** https://redactive.onrender.com
**Interactive docs:** https://redactive.onrender.com/docs

---

## 1. The elevator pitch

Most portfolio DLP projects are a single regex list or a single LLM call.
Redactive is three independent detection layers working together, with a
cost-saving cascade deciding when the expensive layer is worth calling, all
validated against a self-built adversarial evasion suite that measures
exactly how robust the system is — not just whether it "seems to work."

Every claim below is backed by a real, reproducible test result, not
intuition.

---

## 2. Architecture overview

```
                    ┌─────────────────────┐
   Text in  ──────▶ │   Guard 1 — Regex    │  fast, cheap, pattern-based
                    │ (SSN, cards, emails,  │  (SSN, AWS keys, credit cards,
                    │  API keys, IPs...)    │   phone numbers, IPv4...)
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   Guard 2 — NER       │  spaCy entity recognition
                    │ (names, orgs, money,  │  (catches things with no
                    │  locations...)        │   fixed pattern at all)
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  Cascade decision     │  skip Guard 3 only if NO
                    │ (pattern finding OR   │  pattern finding AND NO
                    │  risk keyword?)       │  risk-signaling language
                    └──────────┬───────────┘
                          yes  │  no → skip (saves cost/latency)
                    ┌──────────▼───────────┐
                    │  Guard 3 — LLM        │  Groq (Llama 3.3 70B),
                    │ (contextual judgment, │  temperature=0 for
                    │  explains its score)  │  reproducibility
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  Combine + dedupe     │  merges overlapping findings,
                    │                       │  keeps highest-severity one
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  Redact               │  builds a safe version of
                    │                       │  the text with spans masked
                    └──────────┬───────────┘
                               │
                          Risk report + redacted text
```

**Why three layers instead of one:** each layer catches what the others
structurally cannot.
- Regex catches fixed-format data instantly and cheaply, but is blind to
  anything obfuscated or context-dependent.
- NER catches free-form entities (names, orgs, money) regex can't pattern-
  match, but has no judgment — it's just recognizing shapes of language.
- The LLM is the only layer that understands *meaning*: "our Q3 revenue is
  $4.2M, don't share this outside the team" has no fixed pattern, but is
  obviously risky because of what it says, not how it's formatted.

---

## 3. Key finding #1 — Adversarial evasion testing (94% detection)

Built a self-contained test suite (`evasion_tests/`) that generates 10
obfuscation techniques (leetspeak, spacing, reversal, base64, zero-width
characters, homoglyphs, splitting across sentences, etc.) applied to 5
sensitive-data test cases (SSN, email, AWS key, credit card, email with
extra context), then measures detection rate per technique per layer.

**Headline result: 47/50 (94%) detection**, up from a 62.5% pattern-only
baseline (regex + NER with no LLM layer at all).

### The investigation that got there (the actual interview story)

1. **Initial finding:** email obfuscation was the weakest category —
   spaced-out, reversed, and zero-width-injected emails were slipping
   through even with the LLM layer active.
2. **Hypothesis 1 (wrong):** guessed the LLM needed more contextual
   anchoring — a nearby word like "email" to know what it was looking at.
   Tested this directly: ran the identical obfuscated value through two
   carrier sentences, one that said "email address" and one that didn't.
   **Both performed identically** — hypothesis disproven by the data.
3. **Root cause (found instead):** the LLM's system prompt explicitly told
   it to defer to regex on "plain emails" — a reasonable-sounding rule that
   had a blind spot: it never said "*unless regex already failed due to
   obfuscation*." So when obfuscation broke regex, nothing stepped in.
4. **Fix:** rewrote the prompt to flag anything that *looks* disguised
   (unusual spacing, encoding, symbol substitution) even without full
   certainty. Detection jumped from **82% → 94%** immediately.
5. **Remaining known gap:** `reversed_text` stays around 60% detection.
   Reasoning: reversing a string destroys almost all human-readable
   structure — unlike the other techniques, there's little partial signal
   left for the LLM to reason from. **Deliberate decision not to chase this
   further with more prompt engineering** — a narrow "try reversing
   suspicious strings" instruction would only help this one technique and
   risks false positives elsewhere. The correct fix would be a dedicated
   de-obfuscation preprocessing stage — noted as future work, not solved
   here, to avoid overfitting the prompt to this specific test set.

Full results: `evasion_tests/report/evasion_report.md`

---

## 4. Key finding #2 — Cascade logic (cost savings without losing detection)

**The idea:** don't call the LLM on every request — only when regex/NER
already found something, or the text contains risk-signaling language.
Skipping calls on genuinely unremarkable text ("let's meet at 3pm
tomorrow") saves real cost and latency.

**The naive version broke detection — and the fix is the real story:**

1. First implementation used a narrow keyword list (`"credit card"`,
   `"social security"`, etc.) to decide whether to call the LLM when no
   pattern finding existed.
2. Ran the evasion suite against it: **detection dropped from 94% to 74%**
   — a 20-point regression, caught immediately because the test suite
   already existed.
3. **Root cause:** real carrier sentences don't reliably use the formal
   term for the data type. *"Charge the card..."* doesn't contain the
   phrase "credit card." *"You can reach me at..."* doesn't mention "email"
   at all. The keyword list was too narrow for how people actually write.
4. **Fix:** broadened the keyword list based on the actual gaps found,
   re-ran the suite: **back to 92%**, then to a full **94%** after also
   pinning `temperature=0` on the LLM call to eliminate run-to-run
   scoring variance that was causing one more case to flicker.

This is the complete engineering loop: build → test against existing
suite → catch regression → root-cause it → fix → re-verify. The regression
never shipped silently because the evasion suite was already in place to
catch it.

---

## 5. Security & deployment

- **Deployed on Render** (free tier), Docker-based build, live at
  `https://redactive.onrender.com`
- **API key auth**: every `/analyze` call requires a valid `X-API-Key`
  header (implemented via FastAPI's `APIKeyHeader` security scheme, so it
  shows up correctly as an "Authorize" flow in the Swagger docs)
- **Rate limiting**: 30 requests per 60 seconds per key, in-memory sliding
  window — documented limitation: resets on restart, doesn't share state
  across multiple instances (would need Redis to scale beyond one process)
- **Secrets never committed**: `.env` is gitignored from the start;
  `GROQ_API_KEY` and `REDACTIVE_API_KEY` are set as environment variables
  directly in Render's dashboard, never in code

---

## 6. Chrome extension

A working Manifest V3 extension (`extension/`) that:
- Watches text fields on any webpage (textareas, inputs, contenteditable)
- Debounces 1.2s after typing stops, calls the deployed API via a
  background service worker (not the content script directly — avoids
  CORS/CSP restrictions individual pages might impose)
- Shows an inline warning banner with the live risk score and explanation

**Real bug found and fixed during testing, not just built and assumed
working:** the first version tracked one warning banner per DOM element.
Gmail's compose box is a `contenteditable` region that Google's own JS
frequently rebuilds internally — so the tracked element would go stale,
and old warnings would stay on screen even after the risky text was
deleted, until the tab was closed. Fixed by switching to a single shared
banner that's optimistically cleared on every keystroke and only re-shown
if the fresh analysis is still risky — verified working correctly on Gmail
afterward.

**Known platform limitation:** works on any web-based text field (Gmail,
Slack web, ChatGPT, Notion, Google Docs). Does not work in native desktop
apps (Word, Outlook desktop) — Chrome extensions can only reach content
rendered inside the browser's own tabs, which is a hard platform boundary,
not a bug.

---

## 7. What's deliberately not built (and why)

- **Policy-as-code / admin dashboard / feedback loop** — considered early,
  deprioritized in favor of going deep on evasion testing and cascade
  logic instead, since those produced more defensible, measurable results
  in the available time than a shallow pass at all four differentiators.
- **Unit tests (`tests/`)** — the evasion suite effectively serves this
  role and produces far more useful signal (real detection-rate numbers)
  than basic unit tests would have for this specific project.
- **Chrome Web Store publishing** — real cost (icons, privacy policy,
  $5 fee, review process) for limited portfolio value versus the
  "Load unpacked" flow already documented in this repo.
- **De-obfuscation preprocessing stage** — the correct long-term fix for
  the `reversed_text` gap; intentionally left as documented future work
  rather than solved via prompt engineering, to avoid overfitting to the
  test set.

---

## 8. Numbers worth remembering for a conversation

| Metric | Value |
|---|---|
| Evasion suite detection rate (full pipeline) | 94% (47/50) |
| Detection rate, pattern layers only (no LLM) | 62.5% |
| Detection improvement from one prompt fix | 82% → 94% |
| Cascade regression found and fixed | 94% → 74% → 92% → 94% |
| Rate limit | 30 requests / 60 seconds per key |
| Deployment | Render, Docker, free tier |
| LLM provider | Groq (Llama 3.3 70B), temperature=0 |