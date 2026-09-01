# Public run ledger

Store public run records under `ledger/runs/`.

A run record contains only the fields defined by `schema/run-ledger-entry.schema.json`:

- protocol version;
- run id;
- workload type;
- state;
- final outcome, when available.

Do not store:

- credentials;
- workload contents;
- request or output digests;
- logs;
- traces;
- telemetry;
- diagnostic explanations;
- undocumented fields.

The ledger is an attestation record for public run status, not a diagnostic or reconstruction
record.
