from fastapi import FastAPI
from pydantic import BaseModel
from app.guards.regex_guard import scan_regex
from app.guards.ner_guard import scan_ner

app = FastAPI(
    title="Redactive",
    description="LLM-powered Data Loss Prevention classifier — regex, NER, and LLM layers.",
    version="0.2.0",
)


class AnalyzeRequest(BaseModel):
    text: str


class AnalyzeResponse(BaseModel):
    text: str
    findings: list
    risk_score: int
    layers_used: list


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    """
    Step 2 version: regex + NER layers.
    LLM layer gets added on top of this in Step 3.
    """
    regex_findings = scan_regex(req.text)
    ner_findings = scan_ner(req.text)
    findings = regex_findings + ner_findings

    risk_score = min(100, sum(f["severity"] for f in findings))

    return AnalyzeResponse(
        text=req.text,
        findings=findings,
        risk_score=risk_score,
        layers_used=["regex", "ner"],
    )
