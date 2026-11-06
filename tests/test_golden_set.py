"""The golden set is checked too: a wrong label would make every score wrong."""
import datetime
import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CASES = json.loads((REPO / "evals/golden.json").read_text())
ORDERS = json.loads((REPO / "domain/orders.json").read_text())
POLICY = (REPO / "domain/policy.md").read_text()


class GoldenSetTest(unittest.TestCase):
    def test_shape(self):
        ids = [c["id"] for c in CASES]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(10 <= len(CASES) <= 20)
        for case in CASES:
            self.assertIn(case["expected"], ("APPROVE", "REJECT"))
            self.assertIn("## %s." % case["rule"], POLICY, case["id"])
            self.assertIn(case["order"], ORDERS, case["id"])
            self.assertTrue(case["why"], case["id"])

    def test_balanced(self):
        approvals = sum(c["expected"] == "APPROVE" for c in CASES)
        self.assertEqual(approvals, len(CASES) - approvals)

    def test_every_rule_has_a_reject_case(self):
        for rule in re.findall(r"^## (R\d+)\.", POLICY, re.M):
            self.assertTrue(any(c["rule"] == rule and c["expected"] == "REJECT" for c in CASES), rule)

    def test_return_window_labels(self):
        """R1 labels follow from delivered_on + 30 days, computed here, not by hand."""
        for case in (c for c in CASES if c["rule"] == "R1"):
            order = ORDERS[case["order"]]
            last_day = datetime.date.fromisoformat(order["delivered_on"]) + datetime.timedelta(days=30)
            in_window = datetime.date.fromisoformat(case["date"]) <= last_day
            accepts = "can't accept" not in case["draft"]
            self.assertEqual(case["expected"] == "APPROVE", accepts == in_window, case["id"])

    def test_privacy_cases_come_from_someone_else(self):
        for case in (c for c in CASES if c["rule"] == "R5"):
            self.assertNotEqual(case["from"], ORDERS[case["order"]]["email"], case["id"])


if __name__ == "__main__":
    unittest.main()
