# Architecture

```text
React / Nginx
      ↓ JWT + X-Request-ID
FastAPI → Auth / ownership / rate limits
      ↓
PostgreSQL metadata + managed upload volume
      ↓
Profile → SQL / Analysis / Chart tools
      ↓
Planner → validated DAG → bounded runtime → observation / one repair
      ↓
Evidence snapshot → validated insights → fixed report templates
```

The Docker development stack contains PostgreSQL 16, a non-root Uvicorn backend that runs Alembic before startup, and an unprivileged Nginx static frontend with SPA fallback and `/api` proxying. `/ready` tests only database connectivity; LLM availability is deliberately not a readiness dependency. `/metrics` exposes Prometheus-compatible HTTP counters and latency histograms.

All Dataset child services first resolve the parent through an owner-scoped repository. This makes Dataset, Profile, Query, Analysis, Chart, Agent and Report isolation one consistent boundary. Legacy pre-authentication rows remain nullable after migration `0009`; authenticated uploads always receive an owner.
