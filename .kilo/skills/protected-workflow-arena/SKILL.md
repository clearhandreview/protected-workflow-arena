---
name: protected-workflow-arena
description: Validate, submit, and check AI workflow or Kubernetes test runs through the repository's public Arena CLI.
---

# Protected Workflow Arena

Use this skill when a task asks to test, submit, replay, or check the result of an AI workflow or
Kubernetes workload through Arena.

## Commands

Validate locally:

```bash
python3 cli/arena.py validate --kind ai --file <PATH>
python3 cli/arena.py validate --kind kubernetes --file <PATH>
```

Submit:

```bash
python3 cli/arena.py submit --kind ai --file <PATH>
python3 cli/arena.py submit --kind kubernetes --file <PATH>
```

Check:

```bash
python3 cli/arena.py status <RUN_ID>
```

Save the public result:

```bash
python3 cli/arena.py status <RUN_ID> --kind <ai|kubernetes> --save-ledger
```

## Rules

- Use `cli/arena.py` as the only Arena integration boundary.
- Do not construct direct service requests, enumerate service routes, or probe transport behavior.
- Require `ARENA_API_URL` for network operations.
- Use `ARENA_API_TOKEN` only from the process environment when authentication is required.
- Report only the JSON printed by the CLI.
- Do not infer why a run produced its outcome.
- Do not request or add undocumented telemetry, diagnostic, tuning, trace, digest, or backend fields.
- Do not store credentials, workload contents, request digests, or output digests in the run ledger.
