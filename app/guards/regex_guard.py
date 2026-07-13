"""
Guard 1 — regex layer.

Fast, cheap, catches things with a fixed, recognizable shape.
Every pattern here is intentionally simple and explainable — the point of
this layer is speed, not cleverness. Ambiguous or context-dependent cases
are left for Guard 2 (NER) and Guard 3 (LLM).
"""

import re

PATTERNS = {
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    "phone_us": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "aws_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "generic_api_key": re.compile(r"\b(?:sk|pk|key)-[A-Za-z0-9]{16,}\b"),
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
}

# Human-readable severity per finding type — feeds the risk score
SEVERITY = {
    "ssn": 40,
    "credit_card": 35,
    "aws_key": 40,
    "generic_api_key": 35,
    "email": 10,
    "phone_us": 15,
    "ipv4": 10,
}


def scan_regex(text: str) -> list[dict]:
    """
    Scans text against all known patterns.
    Returns a list of findings: type, matched span, position, severity.
    """
    findings = []
    for label, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            findings.append({
                "type": label,
                "match": match.group(),
                "start": match.start(),
                "end": match.end(),
                "severity": SEVERITY.get(label, 20),
                "source": "regex",
            })
    return findings
