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


class AuditChainVerifyDuringAppend(unittest.TestCase):
    """verify() must never crash while writers are appending, and must report intact chains."""

    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "audit.jsonl")

    def test_verify_while_parallel_writers_append(self):
        workers, per_worker = 4, 40
        jobs = [(self.path, w, per_worker) for w in range(workers)]
        audit_chain.append(self.path, "seed", "first entry")  # file exists before writers start
        errors, false_breaks, checks = [], [], 0
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_writer, job) for job in jobs]
            while not all(f.done() for f in futures):
                try:
                    result = audit_chain.verify(self.path)
                except Exception as exc:  # any crash from a reader is a failure
                    errors.append(f"{type(exc).__name__}: {exc}")
                    break
                checks += 1
                if result != 0:
                    false_breaks.append(result)
            for f in futures:
                f.result()  # surface writer exceptions
        self.assertEqual(errors, [], f"verify crashed during appends after {checks} checks")
        self.assertEqual(false_breaks, [], f"verify reported BROKEN while writers were still running: {false_breaks[:5]}")
        self.assertEqual(audit_chain.verify(self.path), 0)


if __name__ == "__main__":
    unittest.main()
