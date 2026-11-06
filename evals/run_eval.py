"""Run the reviewer on every golden case and score its verdicts.

The reviewer's instructions and model are read from .claude/agents/reviewer.md,
so the eval scores the same instructions and model as the subagent. Each case runs
in a fresh `claude -p` call from an empty directory, in restricted mode (no settings
files), with no tools and no MCP servers.

Usage: python3 evals/run_eval.py [--model sonnet] [--only G01,G09] [--workers 4]
"""
import argparse
import concurrent.futures
import datetime
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENT = ROOT / ".claude/agents/reviewer.md"


def load_agent():
    text = AGENT.read_text()
    _, front, body = text.split("---", 2)
    model = re.search(r"^model:\s*(\S+)", front, re.M)
    return body.strip(), model.group(1) if model else "sonnet"


def build_prompt(instructions, case, orders):
    order = {case["order"]: orders[case["order"]]}
    return "\n\n".join([
        instructions,
        "EVALUATION MODE: do not use any tool. All four inputs are below.",
        "=== domain/policy.md ===\n" + (ROOT / "domain/policy.md").read_text(),
        "=== domain/orders.json (relevant record) ===\n" + json.dumps(order, indent=2),
        "=== ticket ===\nDate: %s\nFrom: %s\nOrder: %s\n\n%s" % (case["date"], case["from"], case["order"], case["message"]),
        "=== outbox/draft.md ===\n" + case["draft"],
    ])


def ask_reviewer(prompt, model):
    """Return (verdict, output). verdict is APPROVE, REJECT, NONE (no verdict line) or ERROR (the call failed)."""
    try:
        with tempfile.TemporaryDirectory() as empty_dir:
            result = subprocess.run(
                ["claude", "-p", prompt, "--model", model, "--restricted", "--tools", "",
                 "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}'],
                cwd=empty_dir, capture_output=True, text=True, timeout=300,
            )
    except (OSError, subprocess.TimeoutExpired) as error:
        return "ERROR", repr(error)
    if result.returncode != 0:
        return "ERROR", (result.stderr or result.stdout).strip()
    found = re.findall(r"VERDICT:\s*(APPROVE|REJECT)", result.stdout)
    return (found[-1] if found else "NONE"), result.stdout.strip()


def score(rows):
    """Split the answers. A failed call is an error, not a judgment: it is never counted as an approval."""
    judged = [r for r in rows if r["got"] != "ERROR"]
    return {
        "correct": sum(r["got"] == r["expected"] for r in judged),
        "judged": len(judged),
        "errors": [r["id"] for r in rows if r["got"] == "ERROR"],
        "false_approvals": [r["id"] for r in judged if r["expected"] == "REJECT" and r["got"] != "REJECT"],
        "false_rejections": [r["id"] for r in judged if r["expected"] == "APPROVE" and r["got"] != "APPROVE"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model")
    parser.add_argument("--only")
    parser.add_argument("--runs", type=int, default=1, help="ask each case this many times, to see how stable the reviewer is")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    instructions, agent_model = load_agent()
    model = args.model or agent_model
    cases = json.loads((ROOT / "evals/golden.json").read_text())
    if args.only:
        cases = [c for c in cases if c["id"] in args.only.split(",")]
    orders = json.loads((ROOT / "domain/orders.json").read_text())
    jobs = [c for c in cases for _ in range(args.runs)]

    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
        answers = list(pool.map(lambda c: ask_reviewer(build_prompt(instructions, c, orders), model), jobs))

    rows = []
    for case, (got, output) in zip(jobs, answers):
        rows.append({"id": case["id"], "rule": case["rule"], "expected": case["expected"], "got": got, "output": output})
        mark = "ok  " if got == case["expected"] else ("ERR " if got == "ERROR" else "FAIL")
        print("%s %s %s expected %-7s got %s" % (mark, case["id"], case["rule"], case["expected"], got))

    result = score(rows)
    answers_by_case = {}
    for r in rows:
        answers_by_case.setdefault(r["id"], set()).add(r["got"])
    unstable = sorted(i for i, seen in answers_by_case.items() if len(seen) > 1)
    print("\n%d/%d correct over %d run(s), model %s" % (result["correct"], result["judged"], args.runs, model))
    print("False approvals (a bad reply would have been sent): %s" % (", ".join(result["false_approvals"]) or "none"))
    print("False rejections (a good reply sent back for rework): %s" % (", ".join(result["false_rejections"]) or "none"))
    if args.runs > 1:
        print("Unstable cases (different answers across runs): %s" % (", ".join(unstable) or "none"))
    if result["errors"]:
        print("Calls that failed, not scored: %s" % ", ".join(result["errors"]))

    out = ROOT / "evals/results" / ("%s-%s-x%d.json" % (datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S"), model, args.runs))
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(dict(result, model=model, date=datetime.date.today().isoformat(), runs=args.runs,
                                   total=len(rows), unstable=unstable, cases=rows), indent=2) + "\n")
    print("Details: %s" % out.relative_to(ROOT))
    return 1 if result["false_approvals"] or result["errors"] else 0

if __name__ == "__main__":
    sys.exit(main())
