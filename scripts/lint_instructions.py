#!/usr/bin/env python3
"""Check that an agent instruction file (CLAUDE.md, AGENTS.md) stays short and has the sections that matter.

    python3 lint_instructions.py CLAUDE.md [--max-lines 150]

Why: long instruction files are skimmed by people and diluted for agents. Treat the file as a
constitution (short, enforceable), and move explanations into docs. Exit code 0 = ok, 1 = problems.
"""
import argparse
import re
import sys

REQUIRED = {
    "evidence": re.compile(r"evidence", re.I),
    "gates": re.compile(r"\bgates?\b|approv", re.I),
    "honesty": re.compile(r"no invented data|unknown stays unknown|never invent", re.I),
    "escalation": re.compile(r"escalat", re.I),
}
PLACEHOLDER = re.compile(r"<[^<>\n]{2,40}>")


def lint(text, max_lines=150):
    problems = []
    n = len(text.splitlines())
    if n > max_lines:
        problems.append(f"{n} lines (limit {max_lines}): move explanations into docs")
    for name, rx in REQUIRED.items():
        if not rx.search(text):
            problems.append(f"missing section about: {name}")
    left = sorted(set(PLACEHOLDER.findall(text)))
    if left:
        problems.append("unfilled placeholders: " + ", ".join(left))
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--max-lines", type=int, default=150)
    args = ap.parse_args(argv)
    with open(args.file, encoding="utf-8") as f:
        problems = lint(f.read(), args.max_lines)
    if problems:
        print("\n".join("- " + p for p in problems))
        return 1
    print("OK: short enough, key sections present, no placeholders left")
    return 0


if __name__ == "__main__":
    sys.exit(main())
