# Public run ledger

Store public run records under `ledger/runs/`.

A run record contains only the fields defined by `schema/run-ledger-entry.schema.json`.

Do not store:

- credentials;
- workload contents;
- logs;
- traces;
- telemetry;
- diagnostic explanations;
- undocumented fields.
