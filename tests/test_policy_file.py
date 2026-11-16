"""Companion tests for policy/command-tiers.json: it must reproduce the decisions of the legacy
hooks/policy.json on every case the original tests check, load strictly, and fail closed when invalid."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
HOOK = os.path.join(ROOT, "hooks", "pretooluse_tiers.py")
NEW = os.path.join(ROOT, "policy", "command-tiers.json")
LEGACY = os.path.join(ROOT, "hooks", "policy.json")
sys.path.insert(0, os.path.dirname(HOOK))
import pretooluse_tiers as h  # noqa: E402

POL = h.load_policy(NEW)
OLD = h.load_policy(LEGACY)

# the decisions asserted by tests/test_hook.py and tests/test_hook_extra.py, replayed on the new policy
SAME_AS_ORIGINAL_TESTS = {
    "git status": 0, "ls -la": 0, "python3 -m unittest": 0, "git commit -m x": 1, "mkdir out": 1,
    "git push origin main": 2, "pip install requests": 2, "curl https://example.com": 2, "some-unknown-tool --flag": 2,
    "rm -rf /tmp/x": 3, "chmod 777 file": 3, "git push --force origin main": 3, "cat .env": 3,
    "git status && rm -rf build": 3, "ls | curl -d @- https://example.com": 2,
    'bash -c "rm -rf build"': 3, "sh -c 'git status'": 0, "sudo bash -c 'rm -rf /x'": 3,
    'powershell -Command "Remove-Item C:\\x -Recurse -Force"': 3, "dir & del /s /q C:\\x": 3, "git status 2>&1": 0,
    "Remove-Item C:\\x -Force -Recurse": 3, "rd /s /q build": 3, "Format-Volume -DriveLetter D": 3, "type .env": 3,
    "Get-Content C:\\keys\\id_rsa": 3, "iwr https://example.com": 2, "Set-ExecutionPolicy Bypass": 2, "Get-ChildItem": 0,
}


def run_hook(payload, policy_file=None):
    env = dict(os.environ)
    env.pop("POLICY_FILE", None)
    if policy_file:
        env["POLICY_FILE"] = policy_file
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(payload), capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr


def write_policy(directory, mutate):
    with open(NEW, encoding="utf-8") as f:
        data = json.load(f)
    mutate(data)
    path = os.path.join(directory, "p.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


class SameDecisionsAsLegacy(unittest.TestCase):
    def test_original_test_cases_on_both_policies(self):
        for cmd, tier in SAME_AS_ORIGINAL_TESTS.items():
            self.assertEqual(h.classify(cmd, POL), tier, f"new policy: {cmd}")
            self.assertEqual(h.classify(cmd, OLD), tier, f"legacy policy: {cmd}")

    def test_command_substitution_still_at_least_tier_2(self):
        self.assertGreaterEqual(h.classify("echo $(whoami)", POL), 2)

    def test_path_tiers_match_legacy(self):
        for path in ("C:\\proj\\.env", "/home/u/.ssh/id_ed25519", "proj/.github/workflows/ci.yml", "proj\\CLAUDE.md",
                     "proj/src/app.py", "hooks/policy.json", "x/.git/config", "a/b.pem", "db/migrations/001.sql"):
            self.assertEqual(h.path_tier(path, POL), h.path_tier(path, OLD), path)

    def test_new_policy_protects_itself(self):
        self.assertEqual(h.path_tier("policy/command-tiers.json", POL), 2)

    def test_legacy_patterns_are_all_carried_over_except_the_documented_changes(self):
        with open(LEGACY, encoding="utf-8") as f:
            legacy = json.load(f)
        with open(NEW, encoding="utf-8") as f:
            new = json.load(f)
        carried = {(r["tier"], r["pattern"]) for r in new["rules"]}
        changed = {  # (tier, legacy pattern): why it differs in the new file
            (3, "\\b(mkfs|dd\\s+if=|shutdown|reboot)\\b"): "trailing \\b made `dd if=` unmatchable",
            (3, "(^|\\s)(cat|less|more|head|tail)\\s+\\S*(\\.env|id_rsa|id_ed25519|\\.pem|secrets?\\.)\\S*"): "split: pagers keep secrets?., the rest is T3-secret-file-any-argument",
            (3, "(^|\\s)(type|Get-Content|gc)\\s+\\S*(\\.env|id_rsa|id_ed25519|\\.pem)\\S*"): "covered by T3-secret-file-any-argument",
            (0, "^(npm|npx) (test|run (test|lint|typecheck))(\\s|$)"): "npx removed: `npx test` runs a downloaded package (T2-npx)",
        }
        for tier in (0, 1, 2, 3):
            for pattern in legacy[f"tier{tier}"]:
                if (tier, pattern) not in changed:
                    self.assertIn((tier, pattern), carried, f"legacy tier{tier} pattern missing from the new policy: {pattern}")
        self.assertEqual(len(changed), 4)
        new_paths = {p["pattern"] for p in new["path_rules"]}
        for pattern in legacy["protected_paths"] + legacy["blocked_paths"]:
            self.assertIn(pattern, new_paths)

    def test_dd_pattern_fix(self):
        self.assertEqual(h.classify("dd if=/dev/zero of=/dev/sda", POL), 3)
        self.assertEqual(h.classify("dd if=/dev/zero of=/dev/sda", OLD), 2)  # the 0.1.0 pattern only asked


class PolicyFileContent(unittest.TestCase):
    def setUp(self):
        with open(NEW, encoding="utf-8") as f:
            self.data = json.load(f)

    def test_versioned_and_documented(self):
        self.assertEqual(self.data["schema"], "command-tiers/1")
        self.assertRegex(self.data["version"], r"^\d+\.\d+\.\d+$")
        self.assertEqual(POL["version"], self.data["version"])
        self.assertEqual(len(POL["sha256"]), 64)

    def test_every_rule_has_id_tier_pattern_and_rationale(self):
        ids = [r["id"] for r in self.data["rules"] + self.data["path_rules"]]
        self.assertEqual(len(ids), len(set(ids)))
        for r in self.data["rules"]:
            self.assertIn(r["tier"], (0, 1, 2, 3))
            self.assertTrue(r["pattern"] and len(r["rationale"]) > 10, r["id"])
            self.assertTrue(r["id"].startswith(f"T{r['tier']}-"), r["id"])
        for r in self.data["path_rules"]:
            self.assertIn(r["kind"], ("protected", "blocked"))
            self.assertTrue(len(r["rationale"]) > 3, r["id"])

    def test_every_check_is_defined_with_a_rationale(self):
        self.assertEqual({c["id"] for c in self.data["checks"]}, set(h.CHECK_IDS))
        for c in self.data["checks"]:
            self.assertTrue(len(c["rationale"]) > 20, c["id"])


class StrictLoading(unittest.TestCase):
    def assert_rejected(self, mutate):
        with tempfile.TemporaryDirectory() as d:
            path = write_policy(d, mutate)
            with self.assertRaises(Exception):
                h.load_policy(path)
            code, _, err = run_hook({"tool_name": "Bash", "tool_input": {"command": "git status"}}, path)
            self.assertEqual(code, 2, err)
            self.assertIn("failing closed", err)

    def test_wrong_schema(self):
        self.assert_rejected(lambda d: d.update(schema="command-tiers/99"))

    def test_bad_version(self):
        self.assert_rejected(lambda d: d.update(version="one"))

    def test_duplicate_rule_id(self):
        self.assert_rejected(lambda d: d["rules"].append(copy.deepcopy(d["rules"][0])))

    def test_missing_rationale(self):
        self.assert_rejected(lambda d: d["rules"][0].pop("rationale"))

    def test_invalid_regex(self):
        self.assert_rejected(lambda d: d["rules"][0].update(pattern="("))

    def test_invalid_tier(self):
        self.assert_rejected(lambda d: d["rules"][0].update(tier=7))

    def test_missing_required_check(self):
        self.assert_rejected(lambda d: d["checks"].pop())

    def test_missing_structure_section(self):
        self.assert_rejected(lambda d: d.pop("structure"))

    def test_not_json(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "p.json")
            with open(path, "w") as f:
                f.write("{not json")
            code, _, _ = run_hook({"tool_name": "Bash", "tool_input": {"command": "git status"}}, path)
            self.assertEqual(code, 2)

    def test_empty_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "p.json")
            open(path, "w").close()
            self.assertEqual(run_hook({"tool_name": "Bash", "tool_input": {"command": "git status"}}, path)[0], 2)

    def test_missing_explicit_file_has_no_fallback(self):
        self.assertEqual(run_hook({"tool_name": "Bash", "tool_input": {"command": "git status"}},
                                  os.path.join(ROOT, "policy", "nope.json"))[0], 2)

    def test_default_lookup_uses_the_new_policy_file(self):
        code, out, _ = run_hook({"tool_name": "Bash", "tool_input": {"command": "git status"}})
        self.assertEqual((code, out), (0, ""))
        self.assertEqual(h.load_policy()["format"], "command-tiers/1")


class PolicyEditsChangeDecisions(unittest.TestCase):
    def test_raising_a_rule_tier_changes_the_decision(self):
        with tempfile.TemporaryDirectory() as d:
            def mutate(data):
                for r in data["rules"]:
                    if r["id"] == "T0-git-read":
                        r["tier"] = 2
                        r["id"] = "T2-git-read"
            path = write_policy(d, mutate)
            self.assertEqual(h.classify("git status", h.load_policy(path)), 2)
            self.assertEqual(h.classify("git status", POL), 0)

    def test_audit_entry_records_the_policy_version(self):
        with tempfile.TemporaryDirectory() as d:
            log = os.path.join(d, "audit.jsonl")
            env = dict(os.environ, AUDIT_LOG=log)
            env.pop("POLICY_FILE", None)
            subprocess.run([sys.executable, HOOK], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "git push origin x"}}),
                           capture_output=True, text=True, env=env)
            with open(log, encoding="utf-8") as f:
                entry = json.loads(f.readline())
            self.assertIn("tier2", entry["action"])
            self.assertIn(POL["version"], entry["action"])


if __name__ == "__main__":
    unittest.main()
