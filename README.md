# Protected Workflow Arena — Public Client

A small public client and contract for submitting AI workflows or Kubernetes workloads to a
protected execution service and receiving an opaque run result.

The public contract is intentionally outcome-only. A client can:

- submit a workload;
- check run state;
- retrieve the final public result;
- store that result in the run ledger;
- validate workload files locally.

The contract does not include diagnostic traces, tuning parameters, resource telemetry, decision
details, request digests, or output digests. Transport-only service fields are not displayed or
written to the public ledger.

## Repository layout

```text
.agents/skills/protected-workflow-arena/SKILL.md
.kilo/skills/protected-workflow-arena/SKILL.md
cli/arena.py
schema/run-request.schema.json
schema/run-result.schema.json  # CLI-visible result
schema/run-ledger-entry.schema.json
examples/
ledger/runs/
tests/
PUBLIC_CONTRACT.md
SECURITY.md
PUBLISHING.md
```

## Runtime

Python 3.11+

Dependencies: Python standard library only.

## Kilo CLI usage

Kilo should use this repository through the Arena CLI only. The project skill under
`.kilo/skills/protected-workflow-arena/` tells Kilo which commands are supported.

The service URL and token are transport configuration. They are not an invitation to call service
routes directly, enumerate endpoints, or inspect backend behavior outside the CLI contract.

A project `kilo.json` keeps Arena CLI commands available while leaving unrelated shell commands
behind Kilo's normal approval prompt.

## Configure the client

```bash
export ARENA_API_URL="https://YOUR-ARENA-HOST"
export ARENA_API_TOKEN="<YOUR_TOKEN>"
```

## Validate a workload without sending it

AI workflow:

```bash
python3 cli/arena.py validate --kind ai --file examples/ai-workflow.json
```

Kubernetes workload:

```bash
python3 cli/arena.py validate --kind kubernetes --file examples/kubernetes-job.yaml
```

## Submit a workload

```bash
python3 cli/arena.py submit --kind ai --file path/to/workflow.json
```

or:

```bash
python3 cli/arena.py submit --kind kubernetes --file path/to/job.yaml
```

## Check a run

```bash
python3 cli/arena.py status RUN_ID
```

## Save a public result to the run ledger

```bash
python3 cli/arena.py status RUN_ID --save-ledger
```

Public ledger records are stored under `ledger/runs/`.

## Public outcomes

A finished run returns one of:

- `passed`
- `failed`
- `contained`
- `rejected`
- `timeout`

No diagnostic meaning beyond the named outcome is part of this public contract.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## License

No open-source license has been selected in this package. Add the license that matches the rights
you intend to grant before inviting third parties to copy, modify, or redistribute the repository.
