"""
Combines findings from regex, NER, and LLM guards into one clean list.

Right now (Steps 1-3) findings were just concatenated in main.py, which
means overlapping spans from different guards (e.g. regex catching a phone
number that NER also partially caught as part of a longer entity) show up
as separate, redundant findings. This module fixes that: sorts by position,
merges overlapping spans, and keeps the highest-severity finding when two
guards flag the same region of text.
"""


def _overlaps(a: dict, b: dict) -> bool:
    """True if finding spans a and b overlap at all."""
    return a["start"] < b["end"] and b["start"] < a["end"]


def combine_findings(findings: list[dict]) -> list[dict]:
    """
    Takes the raw concatenated findings from regex_guard + ner_guard and
    returns a deduplicated, position-sorted list. When two findings
    overlap, the higher-severity one wins and the lower one is dropped
    (it's assumed to be describing the same risky span, just less precisely).
    """
    if not findings:
        return []

    sorted_findings = sorted(findings, key=lambda f: f["start"])
    merged = [sorted_findings[0]]

    for current in sorted_findings[1:]:
        last = merged[-1]
        if _overlaps(last, current):
            # Keep whichever has higher severity; drop the other.
            if current["severity"] > last["severity"]:
                merged[-1] = current
            # else: keep `last`, silently drop `current`
        else:
            merged.append(current)

    return merged


def build_report(
    text: str,
    pattern_findings: list[dict],
    llm_result: dict,
) -> dict:
    """
    Assembles the final combined report: deduplicated findings, a single
    risk score blending pattern-based and LLM-based signals, and everything
    the redactor needs to build a safe version of the text.
    """
    combined = combine_findings(pattern_findings)
    pattern_score = sum(f["severity"] for f in combined)
    total_score = min(100, pattern_score + llm_result["risk_score"])

    return {
        "findings": combined,
        "risk_score": total_score,
        "llm_review": llm_result,
    }
