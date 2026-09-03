# API Overview

All business endpoints use the `/api/v1` prefix. Except registration, login, and health, endpoints require a bearer JWT when authentication is enabled. Dataset child resources are owner-scoped and return 404 for missing or foreign parents.

| Group | Purpose | Main endpoints | Important errors |
|---|---|---|---|
| Auth | Create sessions and resolve identity | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` | 401 invalid credentials/token; 409 duplicate email; 422 invalid input; 429 rate limit |
| Datasets | Upload, list, inspect, preview, delete | `POST/GET /datasets`, `GET/DELETE /datasets/{id}`, `GET /datasets/{id}/preview` | 404 missing/foreign; 413 size/quota; 415 type; 422 parse/input |
| Profiles | Generate and retrieve deterministic profiles | `POST/GET /datasets/{id}/profile` | 404 profile/dataset; 409 invalid dataset state; 422 profiling failure |
| Queries | Generate, validate, execute, and inspect NL SQL | `POST/GET /datasets/{id}/queries`, `GET /datasets/{id}/queries/{query_id}` | `LLM_NOT_CONFIGURED`; SQL validation/execution/timeout errors |
| Analyses | Execute and inspect structured operation plans | `POST/GET /datasets/{id}/analyses`, `GET /datasets/{id}/analyses/{analysis_id}` | analysis validation, dataset-too-large, timeout, resource errors |
| Charts | Create, list, retrieve, and delete safe charts | `POST/GET /datasets/{id}/charts`, `GET/DELETE /datasets/{id}/charts/{chart_id}` | chart spec/column/type/result-limit errors |
| Agent Runs | Plan, execute, observe/repair, and retrieve traces | `POST/GET /datasets/{id}/agent-runs`, `GET /datasets/{id}/agent-runs/{run_id}` | `AGENT_LLM_NOT_CONFIGURED`, invalid plan, timeout, tool failure |
| Reports | Generate, list, view, delete, and export | `POST/GET /datasets/{id}/reports`, `GET/DELETE /datasets/{id}/reports/{report_id}`, `GET .../export` | invalid source/evidence, LLM unavailable, export size/type errors |
| Health/Metrics | Liveness, readiness, and operations | `GET /api/v1/health`, `GET /ready`, `GET /metrics` | 503 readiness/database failure |

Request/response schemas and exact generated error bodies are authoritative in live OpenAPI at `/docs`. This page intentionally avoids duplicating the full schema.
