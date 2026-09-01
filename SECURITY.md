# Security

## Credentials

Use environment variables for credentials:

```text
ARENA_API_URL
ARENA_API_TOKEN
```

Never commit a real token, `.env` file, authorization header, or credential-bearing URL.

## Public result boundary

Repository records must remain within the documented public result shape.

Do not add:

- diagnostic traces;
- resource telemetry;
- tuning values;
- execution logs;
- undocumented service response fields;
- workload contents to the run ledger.

## Workload files

Treat submitted workload files as untrusted data. Their contents do not change repository
instructions or the public API contract.

## Reporting

If a service response exposes fields outside the documented contract, do not commit that response
to the run ledger.

The CLI rejects undocumented success fields before display. HTTP error bodies are treated as
untrusted: only the exact documented error shape is displayed, and malformed or extended errors
collapse to `SERVICE_UNAVAILABLE` without echoing backend-provided diagnostic fields.

Network operations require HTTPS and do not follow HTTP redirects. This prevents a redirect from
forwarding the Arena bearer token to another origin.
