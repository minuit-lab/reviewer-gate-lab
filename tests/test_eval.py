"""The eval scores the subagent's own instructions, not a copy."""
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "evals"))
import run_eval  # noqa: E402


class EvalPromptTest(unittest.TestCase):
    def test_prompt_contains_the_reviewer_instructions_and_model(self):
        instructions, model = run_eval.load_agent()
        agent_file = (REPO / ".claude/agents/reviewer.md").read_text()
        self.assertIn(instructions, agent_file)
        self.assertIn("model: %s" % model, agent_file)
        case = json.loads((REPO / "evals/golden.json").read_text())[0]
        orders = json.loads((REPO / "domain/orders.json").read_text())
        prompt = run_eval.build_prompt(instructions, case, orders)
        self.assertTrue(prompt.startswith(instructions))
        self.assertIn(case["draft"], prompt)

    def test_a_failed_call_is_never_counted_as_an_approval(self):
        rows = [{"id": "G01", "expected": "REJECT", "got": "ERROR"},
                {"id": "G02", "expected": "REJECT", "got": "NONE"},
                {"id": "G03", "expected": "APPROVE", "got": "APPROVE"}]
        result = run_eval.score(rows)
        self.assertEqual(result["errors"], ["G01"])
        self.assertEqual(result["false_approvals"], ["G02"])
        self.assertEqual((result["correct"], result["judged"]), (1, 2))


if __name__ == "__main__":
    unittest.main()
