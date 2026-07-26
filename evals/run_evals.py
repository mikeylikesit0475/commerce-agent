#!/usr/bin/env python3
"""
Agent Evaluation Scorecard Runner for commerce-agent.
Evaluates agent routing, tool selection (expected_tool event trace enforcement), response assertions, and execution latency.
Automatically updates the README.md scorecard block inside <!-- EVAL:BEGIN -->...<!-- EVAL:END -->.
"""
import json
import sys
import time
from pathlib import Path

# Add src to pythonpath
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from commerce_agent.agent import run_agent_query_with_events

EVALS_DIR = Path(__file__).parent
CASES_FILE = EVALS_DIR / "cases.json"
README_FILE = EVALS_DIR.parent / "README.md"

def update_readme_scorecard(scorecard_text: str):
    """Update marked block <!-- EVAL:BEGIN -->...<!-- EVAL:END --> in README.md with fresh scorecard."""
    if not README_FILE.exists():
        print(f"Warning: README.md not found at {README_FILE}")
        return

    try:
        content = README_FILE.read_text()
        begin_marker = "<!-- EVAL:BEGIN -->"
        end_marker = "<!-- EVAL:END -->"
        
        if begin_marker in content and end_marker in content:
            pre = content.split(begin_marker)[0]
            post = content.split(end_marker)[1]
            new_content = f"{pre}{begin_marker}\n```text\n{scorecard_text}\n```\n{end_marker}{post}"
            README_FILE.write_text(new_content)
            print(f"Successfully updated scorecard in {README_FILE}")
        else:
            print("Warning: EVAL markers not found in README.md; skipping README update.")
    except OSError as e:
        print(f"Error updating README scorecard: {e}")

def run_evals():
    if not CASES_FILE.exists():
        print(f"Error: Eval cases file not found at {CASES_FILE}")
        return 1

    with open(CASES_FILE, "r") as f:
        cases = json.load(f)

    today_date = time.strftime("%Y-%m-%d")
    header_str = (
        "==========================================================================\n"
        " 🤖 COMMERCE AGENT EVALUATION SCORECARD\n"
        f" Date: {today_date} | Total Test Cases: {len(cases)}\n"
        "==========================================================================\n"
    )
    print(header_str)

    passed_count = 0
    failed_count = 0
    total_latency = 0.0

    table_header = f"{'ID':<10} | {'Case Name':<32} | {'Status':<6} | {'Latency':<8}"
    print(table_header)
    print("-" * 65)

    rows = []

    for case in cases:
        case_id = case["id"]
        name = case["name"]
        prompt = case["prompt"]
        expected_tool = case.get("expected_tool")
        must_contain = case.get("must_contain", [])
        must_not_contain = case.get("must_not_contain", [])

        start_time = time.time()
        try:
            response, events = run_agent_query_with_events(prompt)
            latency = time.time() - start_time
            total_latency += latency

            # Extract called tools from event trace
            called_tools = []
            for event in events:
                if hasattr(event, "content") and event.content:
                    for part in event.content.parts:
                        if hasattr(part, "function_call") and part.function_call:
                            called_tools.append(part.function_call.name)

            passed = True
            failure_reasons = []

            # 1. Assert expected_tool invocation from event trace
            if expected_tool is None or (isinstance(expected_tool, str) and expected_tool.lower() in ("none", "null")):
                if called_tools:
                    passed = False
                    failure_reasons.append(f"Expected NO tool call, but called: {called_tools}")
            else:
                if expected_tool not in called_tools:
                    passed = False
                    failure_reasons.append(f"Expected tool '{expected_tool}' was NOT invoked (called: {called_tools})")

            # 2. Assert must_contain substrings
            for substring in must_contain:
                if substring.lower() not in response.lower():
                    passed = False
                    failure_reasons.append(f"Missing required substring '{substring}'")

            # 3. Assert must_not_contain substrings
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

            row_line = f"{case_id:<10} | {name[:32]:<32} | {status_str:<6} | {latency:.2f}s"
            print(row_line)
            rows.append(row_line)

            if not passed:
                print(f"   ↳ Failure Reasons: {', '.join(failure_reasons)}")
                print(f"   ↳ Called Tools: {called_tools}")
                print(f"   ↳ Response Snippet: {response[:150]}...\n")

        except Exception as e:  # noqa: BLE001
            latency = time.time() - start_time
            total_latency += latency
            failed_count += 1
            row_line = f"{case_id:<10} | {name[:32]:<32} | FAIL   | {latency:.2f}s"
            print(row_line)
            rows.append(row_line)
            print(f"   ↳ Exception Raised: {e!s}\n")

    total_cases = len(cases)
    pass_pct = (passed_count / total_cases) * 100 if total_cases > 0 else 0.0
    avg_latency = total_latency / total_cases if total_cases > 0 else 0.0

    summary_str = (
        f"-----------------------------------------------------------------\n\n"
        f"📊 FINAL EVALUATION SCORECARD:\n"
        f"   - Total Passed: {passed_count}/{total_cases} ({pass_pct:.1f}%)\n"
        f"   - Total Failed: {failed_count}/{total_cases}\n"
        f"   - Average Response Latency: {avg_latency:.2f}s\n"
        f"=========================================================================="
    )
    print("-" * 65)
    print("\n📊 FINAL EVALUATION SCORECARD:")
    print(f"   - Total Passed: {passed_count}/{total_cases} ({pass_pct:.1f}%)")
    print(f"   - Total Failed: {failed_count}/{total_cases}")
    print(f"   - Average Response Latency: {avg_latency:.2f}s")
    print("==========================================================================")

    # Format full scorecard text to update README.md block
    scorecard_block = (
        f"==========================================================================\n"
        f" 🤖 COMMERCE AGENT EVALUATION SCORECARD\n"
        f" Date: {today_date} | Total Test Cases: {total_cases}\n"
        f"==========================================================================\n\n"
        f"{table_header}\n"
        f"-----------------------------------------------------------------\n"
        + "\n".join(rows) + "\n"
        + summary_str
    )
    update_readme_scorecard(scorecard_block)

    return 0 if passed_count >= 12 else 1

if __name__ == "__main__":
    sys.exit(run_evals())
