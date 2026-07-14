"""
Generates obfuscated versions of sensitive data — the same tricks a real
person might use (deliberately or not) to slip PII past a DLP filter.

Each technique takes a piece of sensitive text and returns a disguised
version, plus a short human-readable name used in the report. The point
isn't that these are exotic — most are things a non-technical person would
stumble into naturally (typos, spacing while typing fast, copy-paste
artifacts) as much as anything a deliberate attacker would try.
"""

import base64


def spaced_out(value: str) -> str:
    """S S N style spacing between every character."""
    return " ".join(list(value))


def leetspeak(value: str) -> str:
    """Common letter-to-number substitutions."""
    subs = {"o": "0", "i": "1", "e": "3", "a": "4", "s": "5"}
    return "".join(subs.get(c.lower(), c) for c in value)


def dashes_to_dots(value: str) -> str:
    """Swap common separators — SSNs/phones often written with dots instead of dashes."""
    return value.replace("-", ".")

def dashes_removed(value: str) -> str:
    """Strip separators entirely, running digits together."""
    return value.replace("-", "")


def reversed_text(value: str) -> str:
    """Reverse the string outright — crude, but tests if detection is purely textual."""
    return value[::-1]


def base64_encoded(value: str) -> str:
    """Base64-encode the value, wrapped in a sentence a scanner might not expect."""
    encoded = base64.b64encode(value.encode()).decode()
    return f"here's the value encoded: {encoded}"


def split_across_sentence(value: str, carrier_text: str) -> str:
    """Break the sensitive value into two halves inserted into unrelated text."""
    mid = len(value) // 2
    part1, part2 = value[:mid], value[mid:]
    return f"{carrier_text} first part is {part1}, and separately, the rest is {part2}"


def homoglyph_substitution(value: str) -> str:
    """Replace some Latin letters with visually similar Unicode lookalikes."""
    lookalikes = {"a": "а", "e": "е", "o": "о"}  # Cyrillic lookalikes
    return "".join(lookalikes.get(c.lower(), c) for c in value)


def zero_width_injection(value: str) -> str:
    """Insert zero-width spaces between characters — invisible to a human reader."""
    zwsp = "\u200b"
    return zwsp.join(list(value))


# Registry of all techniques, used by the test runner.
# Each entry: (name, function). Functions taking only `value` are applied
# directly; `split_across_sentence` needs extra context so it's handled
# separately in the runner.
SIMPLE_TECHNIQUES = {
    "spaced_out": spaced_out,
    "leetspeak": leetspeak,
    "dashes_to_dots": dashes_to_dots,
    "dashes_removed": dashes_removed,
    "reversed_text": reversed_text,
    "base64_encoded": base64_encoded,
    "homoglyph_substitution": homoglyph_substitution,
    "zero_width_injection": zero_width_injection,
}
