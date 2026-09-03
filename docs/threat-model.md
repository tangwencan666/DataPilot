# Threat Model

This model covers the current single-backend, PostgreSQL, managed-upload deployment. “Remaining risk” records boundaries rather than hiding them.

| Threat | Attack surface | Mitigation | Remaining risk |
|---|---|---|---|
| Prompt injection | Questions, column names, sample values | System constraints, bounded context, strict plan/tool schemas, allowlists, revalidation | A model can still produce an unusable plan; there is no semantic guarantee |
| SQL injection | Natural-language SQL and identifiers | Structured generation, `sqlglot` AST allowlist, one SELECT/CTE, logical table restriction, parameterized metadata queries | Validator defects remain possible; this is not a general SQL sandbox |
| Destructive SQL | Generated DDL/DML or unsafe functions | Reject DDL/DML, multiple statements, PRAGMA/ATTACH/COPY/INSTALL/LOAD/CALL and side effects | Future dialect/function changes require validator review |
| External SQL reader | File/network/database scan functions | Function/table allowlists and logical `dataset` relation only | New DuckDB features must be evaluated before upgrades |
| Path traversal | Upload names and managed dataset paths | basename handling, UUID filenames, resolved-parent containment, no API path input | Compromised host/storage is out of scope |
| Arbitrary code execution | Analysis or agent input | Discriminated operation DSL, no code/expression/import fields, spawned controlled worker, no Shell/File/Browser tools | Worker has no OS-level sandbox or memory cgroup |
| LLM hallucination | Plans, synthesis, report insights | Structured schemas, tool-grounded results, evidence references, limitation fields | Narrative may still be incomplete or misleading and needs user judgment |
| Cross-user access | Dataset and child resource IDs | JWT authentication and owner-scoped repositories; foreign IDs return 404 | Legacy ownerless rows need administrative handling |
| XSS | Dataset text, charts, report export | React escaping, safe chart option builder, fixed escaped report templates, security headers | Future custom HTML integrations require a new review |
| Resource exhaustion | Large files, expensive plans, many requests | Upload/user quotas, pagination, max steps, result caps, tool/run timeouts, process-local rate limits | No distributed limiter/queue; host memory limits are deployment concerns |
| Secret leakage | Configuration, errors, logs, repository | Environment configuration, ignored `.env`, sanitized errors, metadata-only logs, public-repo audit | No external secret manager or automatic rotation |
| Report HTML injection | Model findings and dataset values | Schema validation, evidence checks, program-owned escaped HTML, no raw model HTML/JS | Export consumers must preserve safe rendering behavior |

Back up PostgreSQL and upload storage together. Dataset deletion cascades metadata and removes the managed file after commit; cleanup failures require operational reconciliation.
