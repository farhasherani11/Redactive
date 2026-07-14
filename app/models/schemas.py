"""
Shared request/response models. Pulled out of main.py so the API's data
shape is defined in one place, separate from routing logic — matters more
as more endpoints get added later (this file is where they'll all import
their request/response shapes from).
"""

from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    text: str


class AnalyzeResponse(BaseModel):
    original_text: str
    redacted_text: str
    findings: list
    risk_score: int
    layers_used: list
    llm_review: dict
