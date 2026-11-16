"""Companion tests: the Claude Code demo in examples/claude-code-permissions behaves as its README says."""
import json
import os
import subprocess
import sys
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
DEMO = os.path.join(ROOT, "examples", "claude-code-permissions")
HOOK = os.path.join(ROOT, "hooks", "pretooluse_tiers.py")
SETTINGS = os.path.join(DEMO, ".claude", "settings.json")


def run_hook(command):
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(payload), capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


class DemoSettings(unittest.TestCase):
    def setUp(self):
        with open(SETTINGS, encoding="utf-8") as f:
            self.cfg = json.load(f)

    def test_permission_lists_present(self):
        perms = self.cfg["permissions"]
        self.assertIn("Bash(git status)", perms["allow"])
        self.assertIn("Bash(git push *)", perms["ask"])
        self.assertIn("Bash(rm -rf *)", perms["deny"])

    def test_hook_registered_and_resolves(self):
        entry = self.cfg["hooks"]["PreToolUse"][0]
        self.assertIn("Bash", entry["matcher"])
        self.assertEqual(entry["hooks"][0]["type"], "command")
        self.assertIn("hooks/pretooluse_tiers.py", entry["hooks"][0]["command"])
        self.assertTrue(os.path.isfile(os.path.normpath(os.path.join(DEMO, "..", "..", "hooks", "pretooluse_tiers.py"))))


class DemoHookDecisions(unittest.TestCase):
    def test_allowed(self):
        code, out, _ = run_hook("git status")
        self.assertEqual((code, out), (0, ""))

    def test_asks(self):
        code, out, _ = run_hook("git push origin main")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_blocked(self):
        code, out, err = run_hook("rm -rf ./build")
        self.assertEqual(code, 2)
        self.assertIn("Blocked (tier 3)", err)

    def test_malformed_input_fails_closed(self):
        p = subprocess.run([sys.executable, HOOK], input="garbage", capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)


if __name__ == "__main__":
    unittest.main()
