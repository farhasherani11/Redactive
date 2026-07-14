"""
Turns evasion_tests/report/raw_results.json into a readable markdown report
with a summary table and per-technique breakdown — the actual artifact you
show in an interview.

Run after run_evasion_suite.py:
    python -m evasion_tests.generate_report
"""

import json
from collections import defaultdict

RESULTS_PATH = "evasion_tests/report/raw_results.json"
REPORT_PATH = "evasion_tests/report/evasion_report.md"


def generate_report():
    with open(RESULTS_PATH, encoding="utf-8") as f:
        results = json.load(f)

    total = len(results)
    caught = sum(1 for r in results if r["detected"])
    overall_rate = round(100 * caught / total, 1) if total else 0

    # Detection rate broken down by technique, across all test cases.
    by_technique = defaultdict(lambda: {"total": 0, "caught": 0})
    for r in results:
        by_technique[r["technique"]]["total"] += 1
        if r["detected"]:
            by_technique[r["technique"]]["caught"] += 1

    lines = []
    lines.append("# Redactive — Adversarial Evasion Report\n")
    lines.append(
        f"**Overall detection rate: {caught}/{total} ({overall_rate}%)** "
        f"across baseline + obfuscated inputs, all three guard layers combined.\n"
    )

    lines.append("## Detection rate by technique\n")
    lines.append("| Technique | Detected | Total | Rate |")
    lines.append("|---|---|---|---|")
    for technique, stats in sorted(by_technique.items()):
        rate = round(100 * stats["caught"] / stats["total"], 1)
        lines.append(f"| {technique} | {stats['caught']} | {stats['total']} | {rate}% |")

    lines.append("\n## Full results\n")
    lines.append("| Test case | Technique | Detected | Layers fired | Risk score |")
    lines.append("|---|---|---|---|---|")
    for r in results:
        mark = "✅" if r["detected"] else "❌"
        layers = ", ".join(r["layers_fired"]) if r["layers_fired"] else "-"
        lines.append(
            f"| {r['test_case']} | {r['technique']} | {mark} | {layers} | {r['risk_score']} |"
        )

    lines.append("\n## Notes\n")
    lines.append(
        "- \"Detected\" means at least one guard flagged the input — either a "
        "pattern/entity finding, or the LLM assigned a risk score of 30 or higher.\n"
        "- Techniques regex/NER alone would be expected to miss (e.g. "
        "`reversed_text`, `base64_encoded`, `zero_width_injection`) are included "
        "specifically to measure how much the LLM layer adds over the first two "
        "guards alone — see which rows show `llm` as the only layer fired.\n"
        "- This report should be regenerated any time a guard's logic changes, "
        "so the numbers stay accurate."
    )

    lines.append("\n## Known limitations\n")
    lines.append(
        "**`reversed_text` remains the weakest technique (~60% detection), "
        "specifically on email values.** This was investigated deliberately:\n\n"
        "1. Initial hypothesis: email misses were caused by a lack of "
        "contextual anchoring in the carrier sentence (no word like \"email\" "
        "near the obfuscated value). A controlled test (`email` vs "
        "`email_with_context`, identical value, only the carrier sentence "
        "changed) disproved this — both variants performed identically.\n"
        "2. Root cause found instead: the LLM system prompt explicitly "
        "instructed the model to defer to regex on \"plain emails,\" with no "
        "exception for cases where regex had actually failed due to "
        "obfuscation. Fixing that instruction raised overall detection from "
        "82% to 94%.\n"
        "3. `reversed_text` is the one technique that didn't fully close after "
        "the fix. Reasoning: reversing a string destroys nearly all "
        "human-readable structure, unlike spacing, leetspeak, or symbol "
        "substitution, which preserve a recognizable shape the LLM can reason "
        "from. There's little partial signal left for the model to catch.\n\n"
        "**Deliberate decision: not fixing this further with prompt "
        "engineering.** A narrow instruction telling the LLM to actively "
        "try reversing suspicious strings would only help this one technique, "
        "and risks increasing false positives elsewhere by making the model "
        "more aggressive about flagging ordinary text. The correct fix would "
        "be a dedicated de-obfuscation preprocessing step (attempt common "
        "reversals/transforms before any guard sees the text) as its own "
        "pipeline stage — noted as a future improvement rather than solved "
        "here, to avoid overfitting the prompt to this test set."
    )

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Report written to {REPORT_PATH}")
    print(f"Overall: {caught}/{total} ({overall_rate}%) detected")


if __name__ == "__main__":
    generate_report()