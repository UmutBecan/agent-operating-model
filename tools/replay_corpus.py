#!/usr/bin/env python3
"""Replay a corpus of command-evasion cases against the PreToolUse hook's classifier.

    python tools/replay_corpus.py                      # default corpus and policy
    python tools/replay_corpus.py --strict             # also fail on under-blocks
    python tools/replay_corpus.py --corpus other.jsonl --policy policy/command-tiers.json

Corpus format (JSON Lines), one case per line:
    {"id": "...", "category": "...", "command": "...", "expected": 3, "max": 3, "note": "..."}
`expected` is the MINIMUM tier the command must get (0 free, 1 logged, 2 ask, 3 block).
`max` (optional) is a ceiling for benign controls, to notice over-blocking.

Outcomes per case:
    ok            actual tier is within [expected, max]
    FALSE ALLOW   expected >= 2 but actual <= 1: the command would run without a human
    under-block   expected 3 but actual 2: a human is asked, but the policy meant to block
    over          actual > max: a benign command is held back (informational)

Exit code: 1 on any FALSE ALLOW (or any under-block with --strict), else 0.
This measures one hook against one hand-written corpus. It is not proof that the hook is a
security boundary: a corpus can only show the bypasses someone thought of.

Python standard library only.
"""
import argparse
import collections
import inspect
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "hooks"))
import pretooluse_tiers as hook  # noqa: E402

DEFAULT_CORPUS = os.path.join(ROOT, "tests", "corpus", "bypass_cases.jsonl")


def load_corpus(path):
    cases = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            for key in ("id", "command", "expected"):
                if key not in row:
                    raise ValueError(f"{path}:{n}: missing {key!r}")
            if row["expected"] not in (0, 1, 2, 3):
                raise ValueError(f"{path}:{n}: expected must be 0-3")
            cases.append(row)
    ids = [c["id"] for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate case ids")
    return cases


def outcome(case, actual):
    exp, mx = case["expected"], case.get("max", 3)
    if exp >= 2 and actual <= 1:
        return "FALSE ALLOW"
    if exp == 3 and actual == 2:
        return "under-block"
    if actual > mx:
        return "over"
    return "ok"


def classify(command, pol, windows=False):
    """Call the hook's classifier; an older hook without the `windows` argument is called without it."""
    if "windows" in inspect.signature(hook.classify).parameters:
        return hook.classify(command, pol, windows=windows)
    return hook.classify(command, pol)


def replay(cases, pol):
    results = []
    for case in cases:
        try:
            actual = classify(case["command"], pol, windows=(case.get("tool") == "PowerShell"))
        except Exception as exc:  # the hook fails closed (exit 2) on any error: treat as tier 3
            actual = 3
            case = dict(case, note=(case.get("note", "") + f" [classifier raised {type(exc).__name__}]").strip())
        results.append((case, actual, outcome(case, actual)))
    return results


def summarize(results, out=print):
    counts = collections.Counter(o for _, _, o in results)
    matrix = collections.Counter((c["expected"], a) for c, a, _ in results)
    out(f"cases: {len(results)}")
    out("confusion matrix (rows = expected minimum tier, columns = actual tier)")
    out("            actual 0  actual 1  actual 2  actual 3")
    for e in range(4):
        row = [matrix.get((e, a), 0) for a in range(4)]
        if any(row):
            out(f"expected {e}   " + "  ".join(f"{v:8d}" for v in row))
    out(f"ok: {counts['ok']}   FALSE ALLOW: {counts['FALSE ALLOW']}   under-block: {counts['under-block']}   over: {counts['over']}")
    by_cat = collections.defaultdict(lambda: collections.Counter())
    for c, _, o in results:
        by_cat[c.get("category", "-")][o] += 1
    out("by category (ok / false allow / under-block / over)")
    for cat in sorted(by_cat):
        k = by_cat[cat]
        out(f"  {cat:<18} {k['ok']:3d} / {k['FALSE ALLOW']:3d} / {k['under-block']:3d} / {k['over']:3d}")
    for label in ("FALSE ALLOW", "under-block", "over"):
        rows = [(c, a) for c, a, o in results if o == label]
        if rows:
            out(f"{label} cases:")
            for c, a in rows:
                shown = c["command"].replace("\n", "\\n")
                out(f"  [{c['id']}] expected>={c['expected']} actual={a}  {shown}")
    return counts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--corpus", default=DEFAULT_CORPUS)
    ap.add_argument("--policy", help="policy file (default: the hook's default)")
    ap.add_argument("--strict", action="store_true", help="also exit 1 on under-blocks")
    args = ap.parse_args(argv)
    try:
        cases = load_corpus(args.corpus)
        pol = hook.load_policy(args.policy)
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    counts = summarize(replay(cases, pol))
    failed = counts["FALSE ALLOW"] or (args.strict and counts["under-block"])
    print("RESULT: " + ("FAIL" if failed else "PASS"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
