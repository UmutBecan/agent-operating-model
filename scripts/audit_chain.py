#!/usr/bin/env python3
"""A tamper-evident, append-only action log: each entry carries the SHA-256 of the previous one.

    python3 audit_chain.py append LOG "who" "action" ["evidence"]
    python3 audit_chain.py verify LOG

Changing, deleting or reordering any earlier entry breaks every hash after it, so `verify`
reports the first bad line. This detects edits; it does not prevent them (keep the file
where agents have append-only access, and copy it off-host). No dependencies.

Concurrency: `append` holds an exclusive lock on the log while it reads the last hash and
writes the next entry, so parallel writers (for example two hook processes running parallel
tool calls) cannot both chain onto the same predecessor.
"""
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

try:  # POSIX
    import fcntl
except ImportError:  # Windows
    fcntl = None
    import msvcrt

GENESIS = "0" * 64


def _hash(prev, body):
    payload = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(prev.encode("ascii") + payload).hexdigest()


def _lock(f):
    if fcntl is not None:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    else:
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)


def _unlock(f):
    if fcntl is not None:
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    else:
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)


def append(path, who, action, evidence="", now=None):
    body = {
        "time": (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "who": who,
        "action": action,
        "evidence": evidence,
    }
    with open(path, "a+", encoding="utf-8") as f:
        _lock(f)
        try:
            f.seek(0)
            lines = [ln for ln in f.read().splitlines() if ln.strip()]
            prev = GENESIS
            if lines:
                try:
                    prev = json.loads(lines[-1])["hash"]
                except (ValueError, KeyError, TypeError) as exc:
                    # Refuse to write: a new entry chained onto a damaged tail would hide the damage.
                    raise ValueError(
                        f"audit log tail is not a valid entry ({type(exc).__name__}); not appending"
                    ) from exc
            entry = dict(body, prev=prev, hash=_hash(prev, body))
            f.seek(0, os.SEEK_END)
            f.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        finally:
            _unlock(f)
    return entry


def verify(path):
    """Return 0 if the chain is intact, otherwise the 1-based number of the first bad line."""
    prev = GENESIS
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                body = {k: entry[k] for k in ("time", "who", "action", "evidence")}
                ok = entry.get("prev") == prev and entry.get("hash") == _hash(prev, body)
            except (ValueError, KeyError, TypeError):
                ok = False
            if not ok:
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
