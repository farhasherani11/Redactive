"""
Runs every obfuscation technique against a set of known-sensitive values,
sends each result to the live /analyze endpoint, and records whether the
pipeline still caught it.

This is the artifact that actually matters for the interview story: not
"we built a DLP classifier" but "we measured exactly how robust it is
against obfuscation, and here are the numbers."

Requires the server to already be running locally:
    python -m uvicorn app.main:app --reload

Run this suite with:
    python -m evasion_tests.run_evasion_suite
"""

import json
import requests
from evasion_tests.techniques import SIMPLE_TECHNIQUES, split_across_sentence

API_URL = "http://localhost:8000/analyze"

# Known-sensitive test values, each with a natural carrier sentence.
# These are fake/synthetic values — never use real PII in these tests.
TEST_CASES = [
    {
        "label": "SSN",
        "value": "123-45-6789",
        "carrier": "My social security number is {v}, please keep it safe.",
    },
    {
        "label": "email",
        "value": "farha@example.com",
        "carrier": "You can reach me at {v} for anything urgent.",
    },
    {
        "label": "email_with_context",
        "value": "farha@example.com",
        "carrier": "My email address is {v}, feel free to reach out there.",
    },
    {
        "label": "aws_key",
        "value": "AKIA1234567890ABCDEF",
        "carrier": "The AWS access key for the staging bucket is {v}.",
    },
    {
        "label": "credit_card",
        "value": "4111111111111111",
        "carrier": "Charge the card {v} for this month's invoice.",
    },
]


def detected(response_json: dict) -> bool:
    """
    A test case counts as 'detected' if any guard flagged it — either a
    pattern/entity finding exists, or the LLM assigned a meaningfully
    nonzero risk score (not just background noise).
    """
    has_findings = len(response_json.get("findings", [])) > 0
    llm_score = response_json.get("llm_review", {}).get("risk_score", 0)
    return has_findings or llm_score >= 30


def which_layers_fired(response_json: dict) -> list[str]:
    layers = set(f["source"] for f in response_json.get("findings", []))
    if response_json.get("llm_review", {}).get("risk_score", 0) >= 30:
        layers.add("llm")
    return sorted(layers)


def run_case(text: str) -> dict:
    """
    Sends one case to /analyze. If the request fails for any reason
    (server not running, timeout, unexpected error), returns a
    clearly-marked failure result instead of raising — so one bad
    request doesn't take down the entire suite and lose all prior results.
    """
    try:
        resp = requests.post(API_URL, json={"text": text}, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  [!] Request failed: {e}")
        return {"findings": [], "llm_review": {"risk_score": 0}, "risk_score": 0, "_error": str(e)}


def run_suite() -> list[dict]:
    results = []

    for case in TEST_CASES:
        # Baseline: unobfuscated value, should always be caught.
        baseline_text = case["carrier"].format(v=case["value"])
        baseline_resp = run_case(baseline_text)
        results.append({
            "test_case": case["label"],
            "technique": "baseline (no obfuscation)",
            "text_sent": baseline_text,
            "detected": detected(baseline_resp),
            "layers_fired": which_layers_fired(baseline_resp),
            "risk_score": baseline_resp.get("risk_score", 0),
        })

        # Each simple technique.
        for technique_name, technique_fn in SIMPLE_TECHNIQUES.items():
            obfuscated_value = technique_fn(case["value"])
            text = case["carrier"].format(v=obfuscated_value)
            resp = run_case(text)
            result = {
                "test_case": case["label"],
                "technique": technique_name,
                "text_sent": text,
                "detected": detected(resp),
                "layers_fired": which_layers_fired(resp),
                "risk_score": resp.get("risk_score", 0),
            }
            results.append(result)
            print(f"  {case['label']:12s} | {technique_name:24s} | {'CAUGHT' if result['detected'] else 'missed'}")

        # Split-across-sentence technique (needs different handling).
        split_text = split_across_sentence(case["value"], case["carrier"].format(v="").strip())
        split_resp = run_case(split_text)
        results.append({
            "test_case": case["label"],
            "technique": "split_across_sentence",
            "text_sent": split_text,
            "detected": detected(split_resp),
            "layers_fired": which_layers_fired(split_resp),
            "risk_score": split_resp.get("risk_score", 0),
        })

    return results


if __name__ == "__main__":
    print("Running evasion suite against", API_URL)
    print("Make sure the server is running in another terminal before this starts.\n")

    all_results = []
    try:
        all_results = run_suite()
    finally:
        # Always write whatever we have, even if run_suite() raised partway
        # through — partial results are still useful for debugging.
        import os
        os.makedirs("evasion_tests/report", exist_ok=True)
        with open("evasion_tests/report/raw_results.json", "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2)

    total = len(all_results)
    caught = sum(1 for r in all_results if r["detected"])
    print(f"\nDone. {caught}/{total} obfuscated/baseline cases detected.")
    print("Raw results saved to evasion_tests/report/raw_results.json")
    print("Run 'python -m evasion_tests.generate_report' next to build the markdown report.")
