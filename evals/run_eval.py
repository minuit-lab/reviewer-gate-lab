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
    with tempfile.TemporaryDirectory() as empty_dir:
        result = subprocess.run(
            ["claude", "-p", prompt, "--model", model, "--restricted", "--tools", "",
             "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}'],
            cwd=empty_dir, capture_output=True, text=True, timeout=300,
        )
    found = re.findall(r"VERDICT:\s*(APPROVE|REJECT)", result.stdout)
    return (found[-1] if found else "NONE"), result.stdout.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model")
    parser.add_argument("--only")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    instructions, agent_model = load_agent()
    model = args.model or agent_model
    cases = json.loads((ROOT / "evals/golden.json").read_text())
    if args.only:
        cases = [c for c in cases if c["id"] in args.only.split(",")]
    orders = json.loads((ROOT / "domain/orders.json").read_text())

    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
        answers = list(pool.map(lambda c: ask_reviewer(build_prompt(instructions, c, orders), model), cases))

    rows = []
    for case, (got, output) in zip(cases, answers):
        rows.append({"id": case["id"], "rule": case["rule"], "expected": case["expected"], "got": got, "output": output})
        mark = "ok  " if got == case["expected"] else "FAIL"
        print("%s %s %s expected %-7s got %s" % (mark, case["id"], case["rule"], case["expected"], got))

    correct = sum(r["got"] == r["expected"] for r in rows)
    false_approvals = [r["id"] for r in rows if r["expected"] == "REJECT" and r["got"] != "REJECT"]
    false_rejections = [r["id"] for r in rows if r["expected"] == "APPROVE" and r["got"] != "APPROVE"]
    print("\n%d/%d correct, model %s" % (correct, len(rows), model))
    print("False approvals (a bad reply would have been sent): %s" % (", ".join(false_approvals) or "none"))
    print("False rejections (a good reply sent back for rework): %s" % (", ".join(false_rejections) or "none"))

    out = ROOT / "evals/results" / ("%s-%s.json" % (datetime.date.today().isoformat(), model))
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"model": model, "date": datetime.date.today().isoformat(), "correct": correct,
                               "total": len(rows), "false_approvals": false_approvals,
                               "false_rejections": false_rejections, "cases": rows}, indent=2) + "\n")
    print("Details: %s" % out.relative_to(ROOT))
    return 0 if not false_approvals else 1


if __name__ == "__main__":
    sys.exit(main())
