"""Companion tests for the extended hook: wrappers, Windows commands, file-write paths, audit of every decision."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HOOK = os.path.join(os.path.dirname(__file__), "..", "hooks", "pretooluse_tiers.py")
sys.path.insert(0, os.path.join(os.path.dirname(HOOK)))
sys.path.insert(0, os.path.join(os.path.dirname(HOOK), "..", "scripts"))
import pretooluse_tiers as h  # noqa: E402

POL = h.load_policy(os.path.join(os.path.dirname(HOOK), "policy.json"))


def run(payload, env=None):
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(payload), capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr


class Wrappers(unittest.TestCase):
    def test_bash_c_is_judged_by_inner_command(self):
        self.assertEqual(h.classify('bash -c "rm -rf build"', POL), 3)
        self.assertEqual(h.classify("sh -c 'git status'", POL), 0)

    def test_sudo_prefix(self):
        self.assertEqual(h.classify("sudo bash -c 'rm -rf /x'", POL), 3)

    def test_powershell_wrapper(self):
        self.assertEqual(h.classify('powershell -Command "Remove-Item C:\\x -Recurse -Force"', POL), 3)

    def test_single_ampersand_chain_takes_highest_tier(self):
        self.assertEqual(h.classify("dir & del /s /q C:\\x", POL), 3)

    def test_redirect_ampersand_is_not_a_separator(self):
        self.assertEqual(h.classify("git status 2>&1", POL), 0)


class WindowsCommands(unittest.TestCase):
    def test_tiers(self):
        cases = {"Remove-Item C:\\x -Force -Recurse": 3, "rd /s /q build": 3, "Format-Volume -DriveLetter D": 3,
                 "type .env": 3, "Get-Content C:\\keys\\id_rsa": 3, "iwr https://example.com": 2,
                 "Set-ExecutionPolicy Bypass": 2, "Get-ChildItem": 0}
        for cmd, tier in cases.items():
            self.assertEqual(h.classify(cmd, POL), tier, cmd)


class FileWrites(unittest.TestCase):
    def test_path_tiers(self):
        self.assertEqual(h.path_tier("C:\\proj\\.env", POL), 3)
        self.assertEqual(h.path_tier("/home/u/.ssh/id_ed25519", POL), 3)
        self.assertEqual(h.path_tier("proj/.github/workflows/ci.yml", POL), 2)
        self.assertEqual(h.path_tier("proj\\CLAUDE.md", POL), 2)
        self.assertEqual(h.path_tier("proj/src/app.py", POL), 0)

    def test_write_tool_blocked_and_asked(self):
        code, _, _ = run({"tool_name": "Write", "tool_input": {"file_path": "x/.env", "content": "a"}})
        self.assertEqual(code, 2)
        code, out, _ = run({"tool_name": "Edit", "tool_input": {"file_path": "x/.github/workflows/a.yml"}})
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "ask")
        self.assertEqual(run({"tool_name": "Write", "tool_input": {"file_path": "x/a.py"}})[:2], (0, ""))

    def test_powershell_tool_is_judged(self):
        self.assertEqual(run({"tool_name": "PowerShell", "tool_input": {"command": "rd /s /q C:\\x"}})[0], 2)


class AuditOfEveryDecision(unittest.TestCase):
    def test_ask_and_block_are_logged(self):
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, "audit.jsonl")
            env = dict(os.environ, AUDIT_LOG=log)
            run({"tool_name": "Bash", "tool_input": {"command": "git push origin x"}}, env)
            run({"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}, env)
            run({"tool_name": "Bash", "tool_input": {"command": "git status"}}, env)
            with open(log, encoding="utf-8") as f:
                lines = [json.loads(x) for x in f if x.strip()]
            self.assertEqual(len(lines), 2)  # tier 0 is not logged
            self.assertTrue(any("tier3" in x["action"] for x in lines))
            self.assertTrue(any("tier2" in x["action"] for x in lines))


if __name__ == "__main__":
    unittest.main()
