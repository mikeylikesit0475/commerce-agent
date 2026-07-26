#!/usr/bin/env python3
"""
Agent Evaluation Scorecard Runner for commerce-agent.
Evaluates agent routing, tool selection, response assertions, and execution latency.
"""
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

# Add src to pythonpath
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from commerce_agent.agent import run_agent_query

EVALS_DIR = Path(__file__).parent
CASES_FILE = EVALS_DIR / "cases.json"

def run_evals():
    if not CASES_FILE.exists():
        print(f"Error: Eval cases file not found at {CASES_FILE}")
        return 1

    with open(CASES_FILE, "r") as f:
        cases = json.load(f)

    today_date = time.strftime("%Y-%m-%d")
    print("==========================================================================")
    print(" 🤖 COMMERCE AGENT EVALUATION SCORECARD")
    print(f" Date: {today_date} | Total Test Cases: {len(cases)}")
    print("==========================================================================\n")

    passed_count = 0
    failed_count = 0
    total_latency = 0.0

    print(f"{'ID':<10} | {'Case Name':<32} | {'Status':<6} | {'Latency':<8}")
    print("-" * 65)

    for case in cases:
        case_id = case["id"]
        name = case["name"]
        prompt = case["prompt"]
        must_contain = case.get("must_contain", [])
        must_not_contain = case.get("must_not_contain", [])

        start_time = time.time()
        try:
            if case_id == "store_down":
                with patch.dict("os.environ", {"PS_URL": "http://localhost:59999/api"}):
                    response = run_agent_query(prompt)
            else:
                response = run_agent_query(prompt)

            latency = time.time() - start_time
            total_latency += latency

            # Assertions
            passed = True
            failure_reasons = []

            for substring in must_contain:
                if substring.lower() not in response.lower():
                    passed = False
                    failure_reasons.append(f"Missing required substring '{substring}'")

            for substring in must_not_contain:
                if substring.lower() in response.lower():
                    passed = False
                    failure_reasons.append(f"Contains forbidden substring '{substring}'")

            if passed:
                passed_count += 1
                status_str = "PASS"
            else:
                failed_count += 1
                status_str = "FAIL"

            print(f"{case_id:<10} | {name[:32]:<32} | {status_str:<6} | {latency:.2f}s")

            if not passed:
                print(f"   ↳ Failure Reasons: {', '.join(failure_reasons)}")
                print(f"   ↳ Response Snippet: {response[:150]}...\n")

        except Exception as e:  # noqa: BLE001
            latency = time.time() - start_time
            total_latency += latency
            failed_count += 1
            print(f"{case_id:<10} | {name[:32]:<32} | FAIL   | {latency:.2f}s")
            print(f"   ↳ Exception Raised: {e!s}\n")

    total_cases = len(cases)
    pass_pct = (passed_count / total_cases) * 100 if total_cases > 0 else 0.0
    avg_latency = total_latency / total_cases if total_cases > 0 else 0.0

    print("-" * 65)
    print("\n📊 FINAL EVALUATION SCORECARD:")
    print(f"   - Total Passed: {passed_count}/{total_cases} ({pass_pct:.1f}%)")
    print(f"   - Total Failed: {failed_count}/{total_cases}")
    print(f"   - Average Response Latency: {avg_latency:.2f}s")
    print("==========================================================================")

    return 0 if passed_count >= 13 else 1

if __name__ == "__main__":
    sys.exit(run_evals())
