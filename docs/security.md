# Security Boundaries

DataPilot treats every user, file, model response, and cross-resource identifier as untrusted input. The LLM is a planner and structured-output provider, never a security boundary.

## Implemented controls

- Passwords are hashed with Argon2; signed JWTs expire and authenticated requests resolve the current user.
- Dataset and all child resources use owner-scoped lookup. Foreign resource IDs return 404 to reduce enumeration.
- Uploads enforce allowlisted formats, MIME/extension checks, size/quota limits, UUID storage names, and resolved-parent containment.
- SQL passes `sqlglot` AST allowlists and executes read-only in bounded DuckDB.
- Analysis accepts only a Pydantic operation DSL and runs in a spawned worker with time/result limits.
- Charts accept only `ChartSpec`; safe server code builds ECharts options without raw JavaScript.
- Agent plans and repairs have strict schemas, tool allowlists, DAG validation, fixed budgets, and no bypass parameters.
- Report insights require valid evidence references; fixed Markdown/HTML templates escape content.
- Pagination, question/title lengths, result sizes, upload quotas, and selected endpoint rates are bounded.
- CORS validation, security headers, request IDs, sanitized 500 responses, and metadata-only logging reduce exposure.

Secrets belong in environment variables. Logs do not record authorization headers, passwords, request bodies, API keys, file paths, full datasets, raw prompts, tracebacks, or chain-of-thought. `.env` and runtime uploads are ignored by Git; `.env.example` contains local placeholders only.

## Deployment responsibilities

Before any internet-facing deployment, replace local defaults, restrict origins, terminate TLS, define backup/restore procedures for both volumes, and select secure browser token storage. Multi-replica installations require a shared rate limiter and coordinated job execution. Operators should add monitoring, dependency scanning, secret rotation, and an incident response process appropriate to their environment.

## Explicit non-claims

DataPilot does **not** claim to provide:

- an OS-level sandbox or hardened container/microVM execution boundary;
- enterprise multi-tenant isolation or zero-trust infrastructure;
- malware scanning, content disarm, or forensic file inspection;
- an external secret manager or automated key rotation;
- distributed rate limiting, a WAF, or DDoS protection;
- independent penetration testing or compliance certification.

The analysis subprocess is useful fault and timeout isolation, not a security sandbox. DuckDB plus AST validation is a constrained query boundary, not a universal SQL sandbox. Local Docker Compose is a verified deployment foundation, not proof of production operations at scale.

## Reporting vulnerabilities

Until the repository owner publishes a private security contact, avoid placing exploit details or credentials in public issues. Include affected component, reproducible impact, and remediation suggestion through the chosen private channel.
