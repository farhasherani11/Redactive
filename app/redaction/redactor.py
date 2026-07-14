"""
Builds a redacted version of the input text from the combined findings.

This is what actually makes the tool useful in practice: instead of just
reporting "here's what's risky," it returns a safe version of the message
with sensitive spans replaced by a labeled placeholder — so a caller could
plausibly send the redacted version onward instead of the original.

Deliberately kept separate from combine.py: combining/deduplicating findings
and deciding how to mask text are different concerns, and keeping them in
separate files makes each one easier to test and reason about on its own.
"""


def redact_text(text: str, findings: list[dict]) -> str:
    """
    Replaces each finding's span in the text with a [REDACTED_<TYPE>]
    placeholder. Findings must already be deduplicated (see combine.py) —
    this function assumes spans don't overlap, and processes them in
    reverse order so earlier replacements don't shift the character
    offsets of findings still waiting to be redacted.
    """
    if not findings:
        return text

    # Sort by start position descending — replacing from the end of the
    # string backward means each replacement doesn't invalidate the
    # start/end indices of findings earlier in the text.
    ordered = sorted(findings, key=lambda f: f["start"], reverse=True)

    redacted = text
    for finding in ordered:
        label = finding["type"].replace("ner_", "").upper()
        placeholder = f"[REDACTED_{label}]"
        redacted = redacted[: finding["start"]] + placeholder + redacted[finding["end"] :]

    return redacted
