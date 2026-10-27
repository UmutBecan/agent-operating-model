#!/usr/bin/env python3
"""A tamper-evident, append-only action log: each entry carries the SHA-256 of the previous one.

    python3 audit_chain.py append LOG "who" "action" ["evidence"]
    python3 audit_chain.py verify LOG

Changing, deleting or reordering any earlier entry breaks every hash after it, so `verify`
reports the first bad line. This detects edits; it does not prevent them (keep the file
where agents have append-only access, and copy it off-host). No dependencies.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone

GENESIS = "0" * 64


def _hash(prev, body):
    payload = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(prev.encode("ascii") + payload).hexdigest()


def append(path, who, action, evidence="", now=None):
    prev = GENESIS
    try:
        with open(path, encoding="utf-8") as f:
            lines = [ln for ln in f.read().splitlines() if ln.strip()]
        if lines:
            prev = json.loads(lines[-1])["hash"]
    except FileNotFoundError:
        pass
    body = {"time": (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ"), "who": who, "action": action, "evidence": evidence}
    entry = dict(body, prev=prev, hash=_hash(prev, body))
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
    return entry


def verify(path):
    prev = GENESIS
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            entry = json.loads(line)
            body = {k: entry[k] for k in ("time", "who", "action", "evidence")}
            if entry.get("prev") != prev or entry.get("hash") != _hash(prev, body):
                return n
            prev = entry["hash"]
    return 0


def main(argv):
    if len(argv) >= 5 and argv[1] == "append":
        append(argv[2], argv[3], argv[4], argv[5] if len(argv) > 5 else "")
        return 0
    if len(argv) == 3 and argv[1] == "verify":
        bad = verify(argv[2])
        print("OK: chain intact" if bad == 0 else f"BROKEN at line {bad}")
        return 0 if bad == 0 else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
