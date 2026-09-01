#!/usr/bin/env python3
"""Public client for the Protected Workflow Arena.

Runtime: Python 3.11+
Dependencies: Python standard library only.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PROTOCOL_VERSION = "1.0"
WORKLOAD_TYPES = {"ai", "kubernetes"}
STATES = {"accepted", "running", "finished"}
OUTCOMES = {"passed", "failed", "contained", "rejected", "timeout"}
PUBLIC_ERROR_CODES = {
    "INVALID_REQUEST",
    "UNAUTHORIZED",
    "NOT_FOUND",
    "RATE_LIMITED",
    "SERVICE_UNAVAILABLE",
}
BASE_RESULT_FIELDS = {"protocol_version", "run_id", "state"}
FINISHED_RESULT_FIELDS = BASE_RESULT_FIELDS | {
    "outcome",
    "output_available",
    "request_digest",
    "output_digest",
}
PUBLIC_ERROR_FIELDS = {"protocol_version", "error", "request_id"}
RUN_ID_RE = re.compile(r"^[A-Za-z0-9._:-]+$")
REQUEST_ID_RE = re.compile(r"^req_[A-Za-z0-9_-]{1,64}$")


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


URL_OPENER = urllib.request.build_opener(NoRedirectHandler())


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def media_type_for(path: Path, kind: str) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    if guessed:
        return guessed
    return "application/yaml" if kind == "kubernetes" else "application/json"


def build_request(kind: str, path: Path) -> tuple[dict, str]:
    if kind not in WORKLOAD_TYPES:
        raise ValueError("kind must be ai or kubernetes")
    if not path.is_file():
        raise ValueError(f"workload file not found: {path}")
    data = path.read_bytes()
    if not data:
        raise ValueError("workload file is empty")
    digest = sha256_bytes(data)
    payload = {
        "protocol_version": PROTOCOL_VERSION,
        "workload_type": kind,
        "submission": {
            "filename": path.name,
            "media_type": media_type_for(path, kind),
            "content_base64": base64.b64encode(data).decode("ascii"),
        },
    }
    return payload, digest


def validate_public_result(payload: dict) -> None:
    if not isinstance(payload, dict):
        raise ValueError("result must be an object")
    if payload.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError("unsupported protocol_version")
    run_id = payload.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("run_id is required")
    state = payload.get("state")
    if state not in STATES:
        raise ValueError("invalid state")

    allowed_fields = FINISHED_RESULT_FIELDS if state == "finished" else BASE_RESULT_FIELDS
    if payload.keys() - allowed_fields:
        raise ValueError("service response contains undocumented fields")

    if state == "finished":
        if payload.get("outcome") not in OUTCOMES:
            raise ValueError("finished results require a valid outcome")
        if not isinstance(payload.get("output_available"), bool):
            raise ValueError("finished results require output_available")
        digest = payload.get("request_digest")
        if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
            raise ValueError("finished results require request_digest")
        output_digest = payload.get("output_digest")
        if output_digest is not None and (
            not isinstance(output_digest, str)
            or not re.fullmatch(r"sha256:[0-9a-f]{64}", output_digest)
        ):
            raise ValueError("invalid output_digest")


def sanitize_public_error(raw: bytes) -> dict:
    fallback = {
        "protocol_version": PROTOCOL_VERSION,
        "error": "SERVICE_UNAVAILABLE",
    }
    try:
        decoded = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return fallback
    if not isinstance(decoded, dict):
        return fallback
    if decoded.keys() - PUBLIC_ERROR_FIELDS:
        return fallback
    if decoded.get("protocol_version") != PROTOCOL_VERSION:
        return fallback
    if decoded.get("error") not in PUBLIC_ERROR_CODES:
        return fallback
    request_id = decoded.get("request_id")
    if not isinstance(request_id, str) or not REQUEST_ID_RE.fullmatch(request_id):
        return fallback
    return {
        "protocol_version": PROTOCOL_VERSION,
        "error": decoded["error"],
        "request_id": request_id,
    }


def request_json(method: str, url: str, payload: dict | None = None) -> dict:
    headers = {"Accept": "application/json"}
    token = os.environ.get("ARENA_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = None
    if payload is not None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with URL_OPENER.open(req, timeout=60) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        public_error = sanitize_public_error(exc.read())
        print(json.dumps(public_error, indent=2), file=sys.stderr)
        raise SystemExit(1)
    except urllib.error.URLError:
        print(json.dumps({"error": "SERVICE_UNAVAILABLE"}, indent=2), file=sys.stderr)
        raise SystemExit(1)

    try:
        decoded = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError("service returned invalid JSON") from exc
    if not isinstance(decoded, dict):
        raise ValueError("service response must be an object")
    return decoded


def api_base() -> str:
    value = os.environ.get("ARENA_API_URL", "").strip()
    if not value:
        raise ValueError("ARENA_API_URL is required for network operations")
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("ARENA_API_URL must be an https URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("ARENA_API_URL must not contain credentials, a query, or a fragment")
    return value.rstrip("/")


def cmd_validate(args: argparse.Namespace) -> int:
    payload, digest = build_request(args.kind, Path(args.file))
    summary = {
        "protocol_version": payload["protocol_version"],
        "workload_type": payload["workload_type"],
        "filename": payload["submission"]["filename"],
        "media_type": payload["submission"]["media_type"],
        "request_digest": digest,
        "valid": True,
    }
    print(json.dumps(summary, indent=2))
    return 0


def public_result_view(result: dict) -> dict:
    view = {
        "protocol_version": result["protocol_version"],
        "run_id": result["run_id"],
        "state": result["state"],
    }
    if "outcome" in result:
        view["outcome"] = result["outcome"]
    return view


def cmd_submit(args: argparse.Namespace) -> int:
    payload, _ = build_request(args.kind, Path(args.file))
    result = request_json("POST", api_base() + "/v1/runs", payload)
    validate_public_result(result)
    print(json.dumps(public_result_view(result), indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    if not RUN_ID_RE.fullmatch(args.run_id):
        raise ValueError("invalid run_id")
    result = request_json("GET", api_base() + "/v1/runs/" + args.run_id)
    validate_public_result(result)
    visible = public_result_view(result)
    print(json.dumps(visible, indent=2))
    if args.save_ledger:
        if args.kind is None:
            raise ValueError("--kind is required with --save-ledger")
        entry = {
            **visible,
            "workload_type": args.kind,
        }
        out_dir = Path("ledger/runs")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{result['run_id']}.json"
        out_path.write_text(json.dumps(entry, indent=2) + "\n", encoding="utf-8")
        print(f"SAVED: {out_path}", file=sys.stderr)
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="arena")
    sub = p.add_subparsers(dest="command", required=True)

    v = sub.add_parser("validate")
    v.add_argument("--kind", required=True, choices=sorted(WORKLOAD_TYPES))
    v.add_argument("--file", required=True)
    v.set_defaults(func=cmd_validate)

    s = sub.add_parser("submit")
    s.add_argument("--kind", required=True, choices=sorted(WORKLOAD_TYPES))
    s.add_argument("--file", required=True)
    s.set_defaults(func=cmd_submit)

    st = sub.add_parser("status")
    st.add_argument("run_id")
    st.add_argument("--save-ledger", action="store_true")
    st.add_argument("--kind", choices=sorted(WORKLOAD_TYPES))
    st.set_defaults(func=cmd_status)
    return p


def main() -> int:
    try:
        args = parser().parse_args()
        return args.func(args)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
