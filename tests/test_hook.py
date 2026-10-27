import json
import os
import subprocess
import sys
import unittest

HOOK = os.path.join(os.path.dirname(__file__), "..", "hooks", "pretooluse_tiers.py")
sys.path.insert(0, os.path.join(os.path.dirname(HOOK)))
import pretooluse_tiers as h  # noqa: E402

POL = h.load_policy(os.path.join(os.path.dirname(HOOK), "policy.json"))


def run(payload, env=None):
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(payload), capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr


def bash(cmd):
    return {"tool_name": "Bash", "tool_input": {"command": cmd}}


class Tiers(unittest.TestCase):
    def test_classification(self):
        cases = {
            "git status": 0, "ls -la": 0, "python3 -m unittest": 0,
            "git commit -m x": 1, "mkdir out": 1,
            "git push origin main": 2, "pip install requests": 2, "curl https://example.com": 2,
            "some-unknown-tool --flag": 2,
            "rm -rf /tmp/x": 3, "chmod 777 file": 3, "git push --force origin main": 3, "cat .env": 3,
        }
        for cmd, tier in cases.items():
            self.assertEqual(h.classify(cmd, POL), tier, cmd)

    def test_compound_takes_the_highest_tier(self):
        self.assertEqual(h.classify("git status && rm -rf build", POL), 3)
        self.assertEqual(h.classify("ls | curl -d @- https://example.com", POL), 2)

    def test_command_substitution_is_at_least_tier_2(self):
        self.assertGreaterEqual(h.classify("echo $(whoami)", POL), 2)


class HookProcess(unittest.TestCase):
    def test_free_command_is_allowed_silently(self):
        code, out, err = run(bash("git status"))
        self.assertEqual((code, out), (0, ""))

    def test_blocked_command_exits_2_with_reason(self):
        code, out, err = run(bash("rm -rf /"))
        self.assertEqual(code, 2)
        self.assertIn("Blocked (tier 3)", err)

    def test_ask_tier_returns_ask_decision(self):
        code, out, err = run(bash("git push origin feature"))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_non_bash_tools_are_not_touched(self):
        self.assertEqual(run({"tool_name": "Read", "tool_input": {"file_path": "x"}})[0], 0)

    def test_bad_input_fails_closed(self):
        p = subprocess.run([sys.executable, HOOK], input="not json", capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)

    def test_missing_policy_fails_closed(self):
        env = dict(os.environ, POLICY_FILE=os.path.join(os.path.dirname(HOOK), "does-not-exist.json"))
        self.assertEqual(run(bash("git status"), env)[0], 2)


if __name__ == "__main__":
    unittest.main()
