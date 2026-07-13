"""
Guard 2 — NER layer.

Regex (Guard 1) only catches things with a fixed shape. This layer catches
things that don't have a pattern at all — a person's name, a company, a
location — by using a small pretrained language model that recognizes
entity *categories* from context, not format.

Model: spaCy's en_core_web_sm. Swappable later for a HuggingFace transformer
model if higher accuracy is needed — the interface (scan_ner) stays the same
either way, which is the point of keeping this in its own file.
"""

import spacy

_nlp = spacy.load("en_core_web_sm")

# Only entity types relevant to data-leak risk. spaCy tags many more
# (DATE, CARDINAL, ORDINAL, etc.) that aren't sensitive on their own —
# we deliberately don't flag those, to keep noise/false-positives down.
RELEVANT_LABELS = {
    "PERSON": 15,
    "ORG": 10,
    "GPE": 8,       # geopolitical entity — cities, countries, states
    "LOC": 8,       # non-GPE locations
    "MONEY": 12,
    "NORP": 5,      # nationalities, religious/political groups
}


def scan_ner(text: str) -> list[dict]:
    """
    Scans text for named entities using spaCy.
    Returns findings in the same shape as scan_regex, so the pipeline
    can merge results from both guards without special-casing either.
    """
    doc = _nlp(text)
    findings = []

    for ent in doc.ents:
        if ent.label_ not in RELEVANT_LABELS:
            continue
        findings.append({
            "type": f"ner_{ent.label_.lower()}",
            "match": ent.text,
            "start": ent.start_char,
            "end": ent.end_char,
            "severity": RELEVANT_LABELS[ent.label_],
            "source": "ner",
        })

    return findings
