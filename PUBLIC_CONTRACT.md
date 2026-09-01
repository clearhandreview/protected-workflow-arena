# Public Arena CLI Contract — v1

## Purpose

This contract defines what a user or agent may rely on when invoking the public Arena CLI.

The CLI is the supported integration boundary. Service routes, backend topology, implementation
details, diagnostic data, and private execution records are outside this contract.

## Configuration

Network-backed commands read:

```text
ARENA_API_URL
ARENA_API_TOKEN
```

Treat both as operator-provided configuration. Do not print the token, commit it, or derive
additional service requests from the configured URL.

## Validate

```bash
python3 cli/arena.py validate --kind ai --file <PATH>
python3 cli/arena.py validate --kind kubernetes --file <PATH>
```

Validation is local and does not submit the workload.

## Submit

```bash
python3 cli/arena.py submit --kind ai --file <PATH>
python3 cli/arena.py submit --kind kubernetes --file <PATH>
```

A successful submission exposes only:

```json
{
  "protocol_version": "1.0",
  "run_id": "run_...",
  "state": "accepted"
}
```

## Status

```bash
python3 cli/arena.py status <RUN_ID>
```

A non-final result exposes only:

```json
{
  "protocol_version": "1.0",
  "run_id": "run_...",
  "state": "running"
}
```

A finished result exposes only:

```json
{
  "protocol_version": "1.0",
  "run_id": "run_...",
  "state": "finished",
  "outcome": "passed"
}
```

`outcome` is one of:

- `passed`
- `failed`
- `contained`
- `rejected`
- `timeout`

No diagnostic meaning beyond the named outcome is part of the public contract.

## Public errors

Errors use a fixed public shape and code set. The CLI does not expose arbitrary service-provided
diagnostics.

The public error codes are:

- `INVALID_REQUEST`
- `UNAUTHORIZED`
- `NOT_FOUND`
- `RATE_LIMITED`
- `SERVICE_UNAVAILABLE`

## Run ledger

With `--save-ledger`, the CLI stores only:

- protocol version;
- run id;
- workload type;
- state;
- final outcome, when available.

Request digests, output digests, workload contents, traces, telemetry, diagnostic explanations, and
undocumented service fields are not part of the public ledger.

## Compatibility

Clients should reject an unknown major protocol version unless support has been explicitly added.
