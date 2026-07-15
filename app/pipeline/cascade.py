"""
Cascade decision: should this request bother calling the LLM at all?

The naive version of cascading — "only call the LLM if regex/NER already
found something" — would break the LLM's most valuable job: catching risk
that regex/NER find NOTHING for at all (obfuscated data, pure-context risk
like "our Q3 revenue is $4.2M, don't share this outside the team" when no
pattern/entity triggers). Skipping the LLM whenever pattern findings are
empty would silently undo the biggest capability proven in the evasion
report.

So the trigger here is broader than just "pattern findings exist": it also
checks for risk-signaling language. Only when NEITHER a pattern finding NOR
any risk keyword is present do we skip the LLM — i.e. only for text that
looks genuinely unremarkable on every axis we can cheaply check.

This is a real, documented trade-off, not a free lunch: a message with zero
pattern findings AND zero risk keywords that still somehow constitutes a
leak would be missed by this cascade. That's considered acceptable because
such cases are rare and the keyword list is deliberately broad — the same
kind of documented, deliberate limitation as the reversed_text gap in the
evasion report.
"""

# Deliberately broad and cheap to check — a simple substring scan, not NLP.
# False positives here just mean an LLM call happens when it maybe wasn't
# needed (costs a little money); false negatives mean a risky message with
# no pattern finding slips through uninspected (the real risk to avoid).
#
# NOTE: this list was tuned twice. The first version only included formal
# phrases like "credit card" and "social security" — running the evasion
# suite against it dropped detection from 94% to 74%, because real carrier
# text often uses shorter/looser words ("the card", "reach me at") instead
# of the formal term. That result is the reason this list is broader than
# it originally was — a concrete example of why cascade heuristics need to
# be validated against real test data, not just written and trusted.
RISK_KEYWORDS = {
    "confidential", "secret", "password", "credentials", "credential",
    "api key", "access key", "private key", "token",
    "don't share", "do not share", "internal only", "nda",
    "non-disclosure", "proprietary", "classified", "private",
    "salary", "compensation", "revenue",
    "leak", "leaked", "breach",
    "ssn", "social security",
    "credit card", "card", "card number",
    "bank account", "account number", "account",
    "email", "e-mail", "reach me", "contact me",
    "phone number", "phone",
    "medical", "diagnosis", "health",
    "lawsuit", "settlement", "legal",
}


def should_call_llm(text: str, pattern_findings: list[dict]) -> bool:
    """
    Returns True if the LLM guard should run for this text.

    True when either:
    - regex or NER already found something (worth a second, contextual look), OR
    - the text contains risk-signaling language, even with zero pattern findings

    False only when neither signal is present at all.
    """
    if pattern_findings:
        return True

    lowered = text.lower()
    return any(keyword in lowered for keyword in RISK_KEYWORDS)
