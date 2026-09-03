# Changelog

All notable changes for the first public delivery are summarized here.

## 1.0.0 — 2026-09-03

### Added

- CSV/XLSX dataset management, deterministic profiling, quality analysis, and histories
- Natural-language SQL, controlled analysis DSL, structured chart DSL, and ECharts rendering
- Bounded planner, validated DAG, tool registry, execution/attempt trace, controlled repair, and synthesis
- Evidence-backed reports with validated references and Markdown/HTML export
- React dataset workspace, Analysis Lab, Chart Gallery, AI Analyst, and report viewer

### Security

- `sqlglot` AST SQL validation, read-only DuckDB restrictions, and resource limits
- Spawned structured-analysis worker without arbitrary Python code execution
- Server-owned safe ECharts options without raw JavaScript
- JWT/Argon2 authentication, owner-scoped resources, quotas, rate limiting, security headers, and sanitized errors/logs
- Evidence validation and escaped report rendering

### Infrastructure

- PostgreSQL 16 deployment and nine Alembic revisions through `20260830_0009`
- Docker Compose services for PostgreSQL, non-root backend, and Nginx frontend
- Persistent database/upload volumes, health checks, readiness, metrics, and request IDs
- GitHub Actions backend/frontend quality gates

### Testing

- 249 backend and 6 frontend automated tests
- Real PostgreSQL migration chain and downgrade/upgrade round-trip verification
- Full Compose smoke covering authentication, ownership, data flows, observability, persistence, and cleanup

### Documentation

- Public README, architecture, security and threat-model documentation
- Demo, API, graduation defense, interview, resume, project highlights, and release material

No license has been selected for this repository.
