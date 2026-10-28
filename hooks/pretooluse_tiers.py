#!/usr/bin/env python3
"""Claude Code PreToolUse hook: classify a Bash command into tiers 0-3 (see templates/command-tiers.md).

    tier 0  free      -> allow
    tier 1  logged    -> allow, and append to the audit chain if AUDIT_LOG is set
    tier 2  ask       -> ask the human (permissionDecision "ask")
    tier 3  blocked   -> deny with exit code 2 and a reason on stderr

Fail closed: an unknown command is tier 2, and any error while reading the input or the
policy is tier 3. A hook that crashes can let the action proceed, so everything below is
wrapped and exits 2 on error.

Wire it in .claude/settings.json (check the hook format against your Claude Code version):
  {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command",
     "command": "python3 /path/to/hooks/pretooluse_tiers.py"}]}]}}

Policy lives in policy.json next to this file (or POLICY_FILE). This is an example, not a sandbox:
real isolation needs OS-level controls as well.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SEGMENT_SPLIT = re.compile(r"\s*(?:&&|\|\||;|\||(?<![>&])&(?![>&]))\s*")
SHELL_TOOLS = ("Bash", "PowerShell")
WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
# One level of wrapper is unwrapped so `bash -c "rm -rf x"` is judged by what it runs.
WRAPPER = re.compile(r"^(?:sudo\s+|env\s+(?:\w+=\S*\s+)*|(?:\w+=\S+\s+)+)?"
                     r"(?:bash|sh|zsh|pwsh|powershell(?:\.exe)?|cmd(?:\.exe)?)\s+(?:-\w+\s+)*(?:-c|-Command|/c)\s+(.+)$", re.I)


def load_policy(path=None):
    with open(path or os.environ.get("POLICY_FILE") or os.path.join(HERE, "policy.json"), encoding="utf-8") as f:
        pol = json.load(f)
    keys = ("tier0", "tier1", "tier2", "tier3", "protected_paths", "blocked_paths")
    return {k: [re.compile(p, re.I) for p in pol.get(k, [])] for k in keys}


def path_tier(path, pol):
    """Tier for a file write: 3 = blocked path, 2 = protected path (ask), 0 = open."""
    norm = str(path).replace("\\", "/")
    if any(p.search(norm) for p in pol["blocked_paths"]):
        return 3
    if any(p.search(norm) for p in pol["protected_paths"]):
        return 2
    return 0


def classify_segment(seg, pol):
    seg = seg.strip()
    if not seg:
        return 0
    for tier in (3, 2, 1, 0):  # most restrictive first
        if any(p.search(seg) for p in pol[f"tier{tier}"]):
            return tier
    return 2  # unknown -> ask (fail closed)


def classify(command, pol, depth=2):
    """A compound command takes the highest tier of its parts; command substitution is tier 2.
    A shell wrapper (`bash -c '...'`, `powershell -Command ...`) is judged by what it runs."""
    best = 2 if ("$(" in command or "`" in command) else 0
    for seg in SEGMENT_SPLIT.split(command):
        m = WRAPPER.match(seg.strip()) if depth > 0 else None
        if m:
            best = max(best, classify(m.group(1).strip().strip("\"'"), pol, depth - 1))
        else:
            best = max(best, classify_segment(seg, pol))
    return best


def decide(payload, pol):
    """Return (exit_code, stdout_json_or_None, stderr_text)."""
    tool = payload.get("tool_name")
    if tool in WRITE_TOOLS:
        target = str(payload.get("tool_input", {}).get("file_path", payload.get("tool_input", {}).get("notebook_path", "")))
        tier = path_tier(target, pol)
        command = f"{tool} {target}"
    elif tool in SHELL_TOOLS:
        command = str(payload.get("tool_input", {}).get("command", ""))
        tier = classify(command, pol)
    else:
        return 0, None, ""
    if tier == 3:
        return 2, None, f"Blocked (tier 3) by policy: {command[:120]}"
    if tier == 2:
        out = {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                      "permissionDecisionReason": f"Tier 2 (needs a human): {command[:120]}"}}
        return 0, json.dumps(out), ""
    return 0, None, ""


def main():
    try:
        payload = json.load(sys.stdin)
        pol = load_policy()
        code, out, err = decide(payload, pol)
        log = os.environ.get("AUDIT_LOG")
        if log and payload.get("tool_name") in SHELL_TOOLS + WRITE_TOOLS:
            ti = payload.get("tool_input", {})
            subject = str(ti.get("command", ti.get("file_path", ti.get("notebook_path", ""))))
            tier = path_tier(subject, pol) if payload["tool_name"] in WRITE_TOOLS else classify(subject, pol)
            if tier >= 1:  # tier 1 allowed, tier 2 asked, tier 3 blocked: all are recorded
                sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
                import audit_chain
                audit_chain.append(log, "agent", f"tier{tier} decision", subject[:200])
    except Exception as exc:  # fail closed
        sys.stderr.write(f"Blocked: policy hook error ({type(exc).__name__}); failing closed\n")
        sys.exit(2)
    if out:
        sys.stdout.write(out)
    if err:
        sys.stderr.write(err + "\n")
    sys.exit(code)


if __name__ == "__main__":
    main()
