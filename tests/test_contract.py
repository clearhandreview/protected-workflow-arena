import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("arena_client", ROOT / "cli" / "arena.py")
arena = importlib.util.module_from_spec(spec)
spec.loader.exec_module(arena)


class ArenaContractTests(unittest.TestCase):
    def test_ai_request_is_built(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "workflow.json"
            path.write_text('{"name":"x"}', encoding="utf-8")
            payload, digest = arena.build_request("ai", path)
            self.assertEqual(payload["protocol_version"], "1.0")
            self.assertEqual(payload["workload_type"], "ai")
            self.assertTrue(digest.startswith("sha256:"))

    def test_kubernetes_request_is_built(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "job.yaml"
            path.write_text("apiVersion: batch/v1\nkind: Job\n", encoding="utf-8")
            payload, _ = arena.build_request("kubernetes", path)
            self.assertEqual(payload["workload_type"], "kubernetes")

    def test_finished_public_result(self):
        payload = {
            "protocol_version": "1.0",
            "run_id": "run_test",
            "state": "finished",
            "outcome": "passed",
            "output_available": False,
            "request_digest": "sha256:" + "0" * 64,
        }
        arena.validate_public_result(payload)

    def test_finished_result_requires_outcome(self):
        payload = {
            "protocol_version": "1.0",
            "run_id": "run_test",
            "state": "finished",
            "output_available": False,
            "request_digest": "sha256:" + "0" * 64,
        }
        with self.assertRaises(ValueError):
            arena.validate_public_result(payload)


if __name__ == "__main__":
    unittest.main()
