from fastapi import FastAPI
from pydantic import BaseModel
from app.guards.regex_guard import scan_regex
from app.guards.ner_guard import scan_ner
from app.guards.llm_guard import scan_llm

app = FastAPI(
    title="Redactive",
    description="LLM-powered Data Loss Prevention classifier — regex, NER, and LLM layers.",
    version="0.3.0",
)


class AnalyzeRequest(BaseModel):
    text: str


class AnalyzeResponse(BaseModel):
    text: str
    findings: list
    risk_score: int
    layers_used: list
    llm_review: dict


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    """
    Step 3 version: regex + NER + LLM layers, all combined.
    LLM contributes its own risk_score and explanation on top of the
    pattern/entity findings from the first two guards.
    """
    regex_findings = scan_regex(req.text)
    ner_findings = scan_ner(req.text)
    findings = regex_findings + ner_findings

    llm_result = scan_llm(req.text)

    pattern_score = sum(f["severity"] for f in findings)
    combined_score = min(100, pattern_score + llm_result["risk_score"])

    return AnalyzeResponse(
        text=req.text,
        findings=findings,
        risk_score=combined_score,
        layers_used=["regex", "ner", "llm"],
        llm_review=llm_result,
    )
