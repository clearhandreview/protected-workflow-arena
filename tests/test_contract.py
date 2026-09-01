import importlib.util
import io
import json
import os
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr
from unittest import mock
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


    def test_public_result_rejects_undocumented_fields(self):
        payload = {
            "protocol_version": "1.0",
            "run_id": "run_test",
            "state": "finished",
            "outcome": "passed",
            "output_available": False,
            "request_digest": "sha256:" + "0" * 64,
            "internal_detail": "must never cross the public boundary",
        }
        with self.assertRaisesRegex(ValueError, "undocumented fields"):
            arena.validate_public_result(payload)

    def test_http_error_does_not_print_undocumented_fields(self):
        body = json.dumps(
            {
                "protocol_version": "1.0",
                "error": "INVALID_REQUEST",
                "request_id": "req_test",
                "internal_detail": "must never cross the public boundary",
            }
        ).encode("utf-8")
        error = urllib.error.HTTPError(
            "https://arena.example/v1/runs",
            400,
            "Bad Request",
            {},
            io.BytesIO(body),
        )
        stderr = io.StringIO()
        with mock.patch.object(arena.URL_OPENER, "open", side_effect=error):
            with redirect_stderr(stderr), self.assertRaises(SystemExit):
                arena.request_json("POST", "https://arena.example/v1/runs", {})
        output = stderr.getvalue()
        self.assertIn("SERVICE_UNAVAILABLE", output)
        self.assertNotIn("internal_detail", output)
        self.assertNotIn("must never cross", output)

    def test_documented_http_error_is_preserved(self):
        body = json.dumps(
            {
                "protocol_version": "1.0",
                "error": "INVALID_REQUEST",
                "request_id": "req_test",
            }
        ).encode("utf-8")
        sanitized = arena.sanitize_public_error(body)
        self.assertEqual(
            sanitized,
            {
                "protocol_version": "1.0",
                "error": "INVALID_REQUEST",
                "request_id": "req_test",
            },
        )

    def test_public_result_view_hides_transport_metadata(self):
        result = {
            "protocol_version": "1.0",
            "run_id": "run_test",
            "state": "finished",
            "outcome": "passed",
            "output_available": True,
            "request_digest": "sha256:" + "1" * 64,
            "output_digest": "sha256:" + "2" * 64,
        }
        arena.validate_public_result(result)
        self.assertEqual(
            arena.public_result_view(result),
            {
                "protocol_version": "1.0",
                "run_id": "run_test",
                "state": "finished",
                "outcome": "passed",
            },
        )

    def test_saved_ledger_excludes_transport_metadata(self):
        result = {
            "protocol_version": "1.0",
            "run_id": "run_test",
            "state": "finished",
            "outcome": "passed",
            "output_available": True,
            "request_digest": "sha256:" + "1" * 64,
            "output_digest": "sha256:" + "2" * 64,
        }
        args = arena.argparse.Namespace(run_id="run_test", save_ledger=True, kind="ai")
        with tempfile.TemporaryDirectory() as tmp:
            previous = Path.cwd()
            try:
                os.chdir(tmp)
                with mock.patch.object(arena, "api_base", return_value="https://arena.example"):
                    with mock.patch.object(arena, "request_json", return_value=result):
                        arena.cmd_status(args)
                entry = json.loads(Path("ledger/runs/run_test.json").read_text(encoding="utf-8"))
            finally:
                os.chdir(previous)
        self.assertEqual(
            entry,
            {
                "protocol_version": "1.0",
                "run_id": "run_test",
                "state": "finished",
                "outcome": "passed",
                "workload_type": "ai",
            },
        )

    def test_api_base_requires_https(self):
        with mock.patch.dict("os.environ", {"ARENA_API_URL": "http://arena.example"}):
            with self.assertRaisesRegex(ValueError, "https URL"):
                arena.api_base()

    def test_redirects_are_not_followed(self):
        request = urllib.request.Request("https://arena.example/v1/runs")
        redirected = arena.NoRedirectHandler().redirect_request(
            request,
            None,
            302,
            "Found",
            {},
            "https://other.example/",
        )
        self.assertIsNone(redirected)


if __name__ == "__main__":
    unittest.main()
