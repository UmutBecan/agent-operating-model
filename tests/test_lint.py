import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import lint_instructions as li  # noqa: E402

GOOD = """# Instructions
Owner: Ada.
## Evidence
Show command output before claiming done.
## Gates
Release needs approval by the owner.
## Honesty
No invented data. Unknown stays unknown.
## Escalate
Escalate only for irreversible actions.
"""


class Lint(unittest.TestCase):
    def test_good_file_passes(self):
        self.assertEqual(li.lint(GOOD), [])

    def test_too_long_is_reported(self):
        self.assertTrue(any("lines" in p for p in li.lint(GOOD + "\nx" * 200)))

    def test_missing_sections_are_reported(self):
        out = li.lint("# Only a title\n")
        self.assertTrue(any("evidence" in p for p in out))
        self.assertTrue(any("gates" in p for p in out))

    def test_placeholders_are_reported(self):
        self.assertTrue(any("<your name>" in p for p in li.lint(GOOD + "\nOwner: <your name>\n")))

    def test_shipped_template_has_only_placeholders_to_fill(self):
        path = os.path.join(os.path.dirname(__file__), "..", "templates", "CLAUDE.md")
        with open(path, encoding="utf-8") as f:
            out = li.lint(f.read())
        self.assertEqual([p for p in out if "placeholders" not in p], [])


if __name__ == "__main__":
    unittest.main()
