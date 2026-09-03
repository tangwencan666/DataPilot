# DataPilot 1.0.0 Release Notes

## Highlights

DataPilot 1.0.0 delivers an inspectable structured-data analysis workflow: upload and profile a dataset, run safe SQL/structured analysis, create charts, execute a bounded agent plan with controlled repair, and turn verified artifacts into an evidence-backed report.

## Core features

- CSV/XLSX dataset management, preview, profiles, quality findings, and histories
- Natural-language SQL, controlled dataframe analysis, and structured chart generation
- Planner DAG, SQL/Analysis/Chart tool registry, execution/attempt trace, and synthesis
- Bounded observation and same-tool repair
- Evidence-referenced reports with Markdown/HTML export
- React workspace for datasets, analysis, charts, AI Analyst, and reports

## Safety

- `sqlglot` AST allowlists and bounded DuckDB
- Pydantic analysis DSL in a spawned worker; no arbitrary Python
- Safe ECharts builder; no raw JavaScript
- Maximum-step DAG, tool allowlist, repair/time/result budgets
- Evidence reference validation and escaped report templates
- Argon2/JWT authentication and owner-scoped dataset resources

## Deployment

Docker Compose runs PostgreSQL 16, a non-root FastAPI backend, and unprivileged Nginx frontend with separate persistent database/upload volumes. Alembic owns the nine-revision schema through `20260830_0009`.

## Verification

- 249 backend tests and 6 frontend tests passed
- Ruff, formatting, ESLint, TypeScript, and Vite production build passed
- PostgreSQL 16.15 migrations `0001→0009` and `0009→0008→0009` verified
- Backend/frontend image builds, Compose health, auth/ownership, dataset/profile/analysis/chart, metrics, request IDs, security headers, persistence, and cleanup verified

## Known limitations

The release verification did not call a real LLM because no provider credential was configured. Rate limits are process-local; long tasks are synchronous; uploads use local managed storage; the analysis worker is not an OS sandbox; malware scanning and PDF export are absent; the ECharts lazy chunk remains large.
