import time
from fastapi import FastAPI
from app.guards.regex_guard import scan_regex
from app.guards.ner_guard import scan_ner
from app.guards.llm_guard import scan_llm
from app.pipeline.combine import build_report
from app.pipeline.cascade import should_call_llm
from app.redaction.redactor import redact_text
from app.models.schemas import AnalyzeRequest, AnalyzeResponse

app = FastAPI(
    title="Redactive",
    description="LLM-powered Data Loss Prevention classifier — regex, NER, and LLM layers.",
    version="0.5.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    """
    Step 6 version: adds cascade logic. The LLM only runs when regex/NER
    already found something OR the text contains risk-signaling language —
    skipping the call entirely for genuinely unremarkable text, without
    losing the LLM's ability to catch pure-context and obfuscated risk.
    """
    start = time.perf_counter()

    regex_findings = scan_regex(req.text)
    ner_findings = scan_ner(req.text)
    pattern_findings = regex_findings + ner_findings

    if should_call_llm(req.text, pattern_findings):
        llm_result = scan_llm(req.text)
        llm_result["cascade_skipped"] = False
    else:
        llm_result = {
            "risk_score": 0,
            "explanation": "LLM call skipped by cascade — no pattern findings or risk keywords detected.",
            "flagged_phrases": [],
            "source": "llm",
            "enabled": True,
            "cascade_skipped": True,
        }

    report = build_report(req.text, pattern_findings, llm_result)
    redacted = redact_text(req.text, report["findings"])

    elapsed_ms = round((time.perf_counter() - start) * 1000, 1)

    return AnalyzeResponse(
        original_text=req.text,
        redacted_text=redacted,
        findings=report["findings"],
        risk_score=report["risk_score"],
        layers_used=["regex", "ner", "llm"],
        llm_review={**report["llm_review"], "elapsed_ms": elapsed_ms},
    )