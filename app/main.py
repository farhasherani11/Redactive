from fastapi import FastAPI
from app.guards.regex_guard import scan_regex
from app.guards.ner_guard import scan_ner
from app.guards.llm_guard import scan_llm
from app.pipeline.combine import build_report
from app.redaction.redactor import redact_text
from app.models.schemas import AnalyzeRequest, AnalyzeResponse

app = FastAPI(
    title="Redactive",
    description="LLM-powered Data Loss Prevention classifier — regex, NER, and LLM layers.",
    version="0.4.0",
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    """
    Step 4 version: regex + NER + LLM findings get combined and
    deduplicated, then used to produce a redacted version of the text
    alongside the risk report.
    """
    regex_findings = scan_regex(req.text)
    ner_findings = scan_ner(req.text)
    pattern_findings = regex_findings + ner_findings

    llm_result = scan_llm(req.text)

    report = build_report(req.text, pattern_findings, llm_result)
    redacted = redact_text(req.text, report["findings"])

    return AnalyzeResponse(
        original_text=req.text,
        redacted_text=redacted,
        findings=report["findings"],
        risk_score=report["risk_score"],
        layers_used=["regex", "ner", "llm"],
        llm_review=report["llm_review"],
    )
