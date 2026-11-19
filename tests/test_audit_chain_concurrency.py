import json
import os
import sys
import tempfile
import unittest
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import audit_chain  # noqa: E402


def _writer(args):
    path, worker, count = args
    for i in range(count):
        audit_chain.append(path, f"worker{worker}", f"step {i}", "")
    return count


class AuditChainConcurrency(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "audit.jsonl")

    def test_parallel_appends_keep_one_unbroken_chain(self):
        workers, per_worker = 6, 20
        jobs = [(self.path, w, per_worker) for w in range(workers)]
        with ProcessPoolExecutor(max_workers=workers) as pool:
            done = sum(pool.map(_writer, jobs))
        self.assertEqual(done, workers * per_worker)

        with open(self.path, encoding="utf-8") as f:
            entries = [json.loads(line) for line in f if line.strip()]
        self.assertEqual(len(entries), workers * per_worker)
        # Every entry must chain onto a distinct predecessor: a fork would reuse a `prev`.
        prevs = [e["prev"] for e in entries]
        self.assertEqual(len(set(prevs)), len(prevs))
        self.assertEqual(audit_chain.verify(self.path), 0)

    def test_damaged_tail_is_reported_by_verify_not_crashed(self):
        audit_chain.append(self.path, "agent", "step 0")
        with open(self.path, "a", encoding="utf-8") as f:
            f.write('{"time": "2026-11-19T')  # simulated partial write
        self.assertEqual(audit_chain.verify(self.path), 2)

    def test_append_refuses_to_chain_onto_a_damaged_tail(self):
        audit_chain.append(self.path, "agent", "step 0")
        with open(self.path, "a", encoding="utf-8") as f:
            f.write('{"time": "2026-11-19T')
        with self.assertRaises(ValueError):
            audit_chain.append(self.path, "agent", "step 1")


if __name__ == "__main__":
    unittest.main()
