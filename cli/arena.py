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
import urllib.request
from pathlib import Path

PROTOCOL_VERSION = "1.0"
WORKLOAD_TYPES = {"ai", "kubernetes"}
STATES = {"accepted", "running", "finished"}
OUTCOMES = {"passed", "failed", "contained", "rejected", "timeout"}
RUN_ID_RE = re.compile(r"^[A-Za-z0-9._:-]+$")


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
    if state == "finished":
        if payload.get("outcome") not in OUTCOMES:
            raise ValueError("finished results require a valid outcome")
        if not isinstance(payload.get("output_available"), bool):
            raise ValueError("finished results require output_available")
        digest = payload.get("request_digest")
        if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
            raise ValueError("finished results require request_digest")


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
        with urllib.request.urlopen(req, timeout=60) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            public_error = json.loads(raw.decode("utf-8"))
        except Exception:
            public_error = {"error": "SERVICE_UNAVAILABLE"}
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


def cmd_submit(args: argparse.Namespace) -> int:
    payload, _ = build_request(args.kind, Path(args.file))
    result = request_json("POST", api_base() + "/v1/runs", payload)
    validate_public_result(result)
    print(json.dumps(result, indent=2))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    if not RUN_ID_RE.fullmatch(args.run_id):
        raise ValueError("invalid run_id")
    result = request_json("GET", api_base() + "/v1/runs/" + args.run_id)
    validate_public_result(result)
    print(json.dumps(result, indent=2))
    if args.save_ledger:
        workload_type = args.kind
        digest = result.get("request_digest")
        if workload_type is None:
            raise ValueError("--kind is required with --save-ledger")
        if not digest:
            raise ValueError("service result does not yet include request_digest")
        entry = {
            "protocol_version": PROTOCOL_VERSION,
            "run_id": result["run_id"],
            "workload_type": workload_type,
            "state": result["state"],
            "request_digest": digest,
        }
        if "outcome" in result:
            entry["outcome"] = result["outcome"]
        if "output_digest" in result:
            entry["output_digest"] = result["output_digest"]
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
