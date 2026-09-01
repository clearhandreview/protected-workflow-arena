---
name: protected-workflow-arena
description: Submit and track AI workflow or Kubernetes test runs through the repository's public protected-execution client.
---

# Protected Workflow Arena

Use this skill when a task asks to test, submit, replay, or check the result of an AI workflow or
Kubernetes workload through the arena.

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
python3 cli/arena.py status <RUN_ID> --save-ledger
```

## Rules

- Require `ARENA_API_URL` for network operations.
- Use `ARENA_API_TOKEN` when the service requires authentication.
- Report only fields returned by the public contract.
- Do not infer why a run produced its outcome.
- Do not add undocumented telemetry, diagnostic, tuning, or trace fields.
- Do not store credentials in the run ledger.
