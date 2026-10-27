import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import audit_chain  # noqa: E402
import decision_age  # noqa: E402

REGISTER = """| # | Decision | Recommendation | First asked | Status | Owner |
|---|---|---|---|---|---|
| D1 | Apply the schema change | Yes | 2026-10-20 | OPEN | you |
| D2 | Switch provider to live | Yes | 2026-10-22 | TRIGGER (2026-11-01) | you |
| D3 | Archive test env | Yes | 2026-10-10 | CLOSED (said yes) | you |
"""


class DecisionAge(unittest.TestCase):
    def test_open_rows_have_age_and_closed_rows_are_marked(self):
        rows = decision_age.parse(REGISTER, date(2026, 10, 28))
        by_id = {r["id"]: r for r in rows}
        self.assertEqual(by_id["D1"]["age"], 8)
        self.assertEqual(by_id["D2"]["age"], 6)
        self.assertTrue(by_id["D3"]["status"].startswith("CLOSED"))
        self.assertEqual(len(rows), 3)


class AuditChain(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "audit.jsonl")

    def test_intact_chain_verifies(self):
        audit_chain.append(self.path, "builder", "ran tests", "117 passed")
        audit_chain.append(self.path, "owner", "approved release", "")
        self.assertEqual(audit_chain.verify(self.path), 0)

    def test_editing_an_old_entry_is_detected_at_that_line(self):
        audit_chain.append(self.path, "builder", "ran tests", "117 passed")
        audit_chain.append(self.path, "owner", "approved release", "")
        with open(self.path, encoding="utf-8") as f:
            text = f.read()
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(text.replace("117 passed", "118 passed", 1))
        self.assertEqual(audit_chain.verify(self.path), 1)

    def test_deleting_an_entry_breaks_the_chain(self):
        for i in range(3):
            audit_chain.append(self.path, "agent", f"step {i}")
        with open(self.path, encoding="utf-8") as f:
            lines = f.read().splitlines()
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(lines[0] + "\n" + lines[2] + "\n")
        self.assertEqual(audit_chain.verify(self.path), 2)


if __name__ == "__main__":
    unittest.main()
