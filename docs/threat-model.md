# Threat model

| Threat | Current mitigation | Remaining gap |
|---|---|---|
| Prompt injection | strict plan/tool schemas and allowlist validator | models can still produce unusable plans |
| SQL injection / unsafe generated SQL | sqlglot AST allowlist, read-only bounded DuckDB | not a general SQL sandbox |
| Arbitrary code execution | no shell/file/browser tools; controlled Analysis DSL worker | no OS-level sandbox |
| Path traversal | UUID filenames and resolved-parent containment | malware scanning not included |
| Cross-user access | JWT and owner-scoped Dataset resolution, 404 for foreign IDs | legacy ownerless rows require administrative backfill |
| XSS in reports | schema validation and escaped fixed HTML template; CSP | CSP must be retested after custom integrations |
| DoS/resource exhaustion | request limits, tool timeouts, pagination, quotas, rate limits | distributed limiter/queue absent |
| Secret leakage | env-based secrets, startup validation, sanitized errors/log fields | external secret manager absent |

Back up both PostgreSQL and the managed upload volume. Dataset deletion cascades metadata through foreign keys and removes the managed file after commit; failed file cleanup is logged for operational reconciliation.
