#!/usr/bin/env python3
"""Print the age of every open decision in a decision register (Markdown table).

Usage:  python3 decision_age.py templates/decision-register.md [--today YYYY-MM-DD]

A row counts as open when its Status cell starts with OPEN or TRIGGER. The date is
read from the 'First asked' column (YYYY-MM-DD). No dependencies.
"""
import argparse
import re
import sys
from datetime import date, datetime

ROW = re.compile(r"^\|\s*(?P<id>[^|]+?)\s*\|(?P<cells>.*)\|\s*$")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def parse(text, today):
    rows = []
    for line in text.splitlines():
        m = ROW.match(line)
        if not m or m.group("id").strip("-: ") == "" or m.group("id").lower() == "#":
            continue
        cells = [c.strip() for c in m.group("cells").split("|")]
        status = next((c for c in cells if re.match(r"(OPEN|TRIGGER|CLOSED)", c, re.I)), "")
        asked = next((c for c in cells if DATE.fullmatch(c)), "")
        if not status or not asked:
            continue
        age = (today - datetime.strptime(asked, "%Y-%m-%d").date()).days
        rows.append({"id": m.group("id"), "age": age, "status": status, "text": cells[0]})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("register")
    ap.add_argument("--today", default=date.today().isoformat())
    args = ap.parse_args(argv)
    today = datetime.strptime(args.today, "%Y-%m-%d").date()
    with open(args.register, encoding="utf-8") as f:
        rows = parse(f.read(), today)
    open_rows = sorted((r for r in rows if not r["status"].upper().startswith("CLOSED")), key=lambda r: -r["age"])
    if not open_rows:
        print("No open decisions.")
        return 0
    for r in open_rows:
        print(f"{r['id']:<6} {r['age']:>4} days  {r['status'].split(' ')[0]:<8} {r['text'][:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
