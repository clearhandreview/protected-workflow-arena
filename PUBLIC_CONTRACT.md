# Public Arena Contract — v1

## Purpose

This contract defines the information exchanged between a workflow client and the protected
execution service.

The contract is intentionally narrow so integrations depend only on stable public behavior.

## Authentication

Clients send a bearer token:

```text
Authorization: Bearer <token>
```

## Submit

`POST /v1/runs`

Request body:

```json
{
  "protocol_version": "1.0",
  "workload_type": "ai",
  "submission": {
    "filename": "workflow.json",
    "media_type": "application/json",
    "content_base64": "..."
  }
}
```

`workload_type` is one of:

- `ai`
- `kubernetes`

A successful submission returns:

```json
{
  "protocol_version": "1.0",
  "run_id": "run_...",
  "state": "accepted"
}
```

## Status

`GET /v1/runs/{run_id}`

A run that has not finished returns:

```json
{
  "protocol_version": "1.0",
  "run_id": "run_...",
  "state": "running"
}
```

A finished run returns:

```json
{
  "protocol_version": "1.0",
  "run_id": "run_...",
  "state": "finished",
  "outcome": "passed",
  "output_available": true,
  "request_digest": "sha256:...",
  "output_digest": "sha256:..."
}
```

`outcome` is one of:

- `passed`
- `failed`
- `contained`
- `rejected`
- `timeout`

`output_digest` is optional when no public output exists.

## Public error shape

Errors use a fixed shape:

```json
{
  "protocol_version": "1.0",
  "error": "INVALID_REQUEST",
  "request_id": "req_..."
}
```

The public contract defines these error codes:

- `INVALID_REQUEST`
- `UNAUTHORIZED`
- `NOT_FOUND`
- `RATE_LIMITED`
- `SERVICE_UNAVAILABLE`

Diagnostic fields are not part of the public API.

## Run ledger

The public run ledger records only:

- protocol version;
- run id;
- workload type;
- state;
- final outcome, when available;
- request digest;
- output digest, when available.

The ledger is a result record, not a diagnostic trace.

## Compatibility

Clients should reject an unknown major protocol version unless support has been explicitly added.
