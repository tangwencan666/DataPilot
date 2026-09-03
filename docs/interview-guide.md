# Interview Guide

Use these prompts to explain decisions, trade-offs, failure modes, and extensions—not to recite library definitions.

## Backend and data

### Why FastAPI?

Typed request models, dependency injection, generated OpenAPI, and async-capable HTTP fit a schema-heavy tool platform. The actual analytics are CPU/blocking work, so simply marking handlers async would not solve isolation; workers or a future queue are still needed.

### Why SQLAlchemy and Alembic rather than `create_all`?

SQLAlchemy centralizes persistence and owner-scoped repositories. Alembic makes nine schema transitions reviewable and testable on PostgreSQL. The trade-off is migration maintenance, but reproducible upgrades and rollback checks matter more than startup convenience.

### Why PostgreSQL plus DuckDB?

PostgreSQL owns transactional metadata and histories. DuckDB runs bounded analytical SQL against a logical dataset relation without exposing the application database. One engine could simplify deployment, but would blur permissions and workload roles.

### Where is pandas used safely?

Only validated DSL operations reach a spawned worker. Input path comes from the managed dataset record, operations and columns are allowlisted, and output/time are bounded. Process termination is a reliability control, not a full security sandbox.

### What can go wrong with timeouts?

A cooperative thread timeout may leave work alive. SQL uses DuckDB interruption; analysis uses a process that can be terminated/killed. Agent deadlines stop launching new steps, while each active tool retains its own timeout. A future distributed worker needs cancellation and idempotency.

## Frontend and platform

### What is the React UI’s distinctive role?

It separates Planner, tool execution, observations/attempts, final synthesis, and artifacts instead of showing a single chat bubble. ECharts is lazy-loaded, although its chunk remains large. Future work could reduce the chart import surface.

### Why JWT, and what would you change?

JWT keeps the current Compose topology simple; Argon2 protects password hashes and owner-scoped repositories enforce authorization. localStorage increases XSS exposure, so an internet-facing system should consider secure HttpOnly cookies, CSRF controls, refresh rotation, and revocation policy.

### What does Docker verification prove?

It proves images build, services start together, PostgreSQL migrations work, volumes persist, and real HTTP flows pass in that environment. It does not prove high availability, load capacity, cloud security, or production operations.

## LLM application engineering

### How is structured output different from tool calling?

Structured output constrains the returned shape; the application then validates semantics and chooses whether to execute an allowlisted adapter. Tool calling alone is not authorization. DataPilot’s registry, validators, ownership, and limits remain authoritative.

### How do you handle prompt injection?

Assume it may influence text generation. Limit context, exclude secrets/paths, validate tool names and fields, reject code/path/network patterns, and make the runtime incapable of unregistered actions. The correct goal is impact containment, not claiming prompts are injection-proof.

### Why bounded repair?

Column/type mismatches are common and sometimes repairable, but recursive re-planning expands cost and attack surface. A deterministic classifier decides eligibility; repair keeps step/tool/topology, revalidates, and has strict budgets.

### How would you add a new tool?

Define a strict schema, semantic validator, adapter with standardized bounded results, timeout/resource policy, observation classification, artifact persistence, tests, and prompt capability text. Registration comes last; never expose a generic code tool as a shortcut.

### How do reports reduce hallucination?

The model receives bounded evidence and produces structured insights with references. The application verifies each reference and renders escaped templates. This grounds claims but does not prove causal correctness; limitations and human review remain necessary.

## Observability, testing, and CI

### What is logged?

Request/run/dataset/step/tool/status/duration identifiers and bounded categories. Authorization headers, passwords, API keys, bodies, full results, paths, prompts, tracebacks, and hidden reasoning are excluded.

### What testing strategy is used?

Unit tests target schemas, AST/semantic validators, transformation and repair policy. API tests exercise persistence, auth and ownership. Frontend tests cover critical auth/client behaviors. CI adds PostgreSQL migration verification, Ruff/format, ESLint, tests, and production build. Missing areas include load, browser E2E, fuzzing, and penetration testing.

### What failure scenarios matter most?

Malformed uploads, unknown columns, unsafe SQL, oversized intermediate results, worker timeout, LLM unavailability, invalid evidence references, cross-user IDs, and migration drift. Each should fail closed with a stable status/error and no secret leakage.

## Five STAR stories

### 1. SQL safety

**Situation:** Natural-language SQL made model output executable against user data. **Task:** Support useful analytics without trusting generated text. **Action:** Added structured generation, `sqlglot` AST allowlists, logical-table restriction, external-reader rejection, automatic LIMIT, bounded DuckDB execution, transparency, and validator tests. **Result:** SQL queries pass the same safety path whether called directly or by the Agent; destructive and external-access patterns are rejected in the verified 249-test backend suite.

### 2. Arbitrary Python to structured analysis DSL

**Situation:** General Python would make dataframe analysis flexible but expose filesystem/process/code execution. **Task:** Preserve common analysis workflows with predictable risk. **Action:** Modeled operations as Pydantic discriminated unions, allowlisted operators/aggregations, validated columns, moved execution to a spawned worker, and applied timeout/result/sample rules. **Result:** Filtering, grouping, statistics, time series, derivation, and top-N are available without accepting source code; timeout and serialization paths are covered by tests.

### 3. Controlled agent repair

**Situation:** A fixed plan can fail on a wrong column or aggregation, while unlimited ReAct is unbounded. **Task:** Recover common errors without changing the security model. **Action:** Standardized observations, classified failures deterministically, allowed one same-tool structured repair per step and three per run, persisted attempts, and reapplied every original validator. **Result:** Repairable failures gain a traceable second attempt; security/time/resource/internal failures stop, and the plan topology never expands.

### 4. Real Docker/PostgreSQL release verification

**Situation:** SQLite tests and successful image builds did not prove the actual deployment or migration chain. **Task:** Validate the release on real infrastructure. **Action:** Ran PostgreSQL 16.15 migrations `0001→0009`, downgrade/upgrade round-trip, full Compose health, auth/ownership, dataset/profile/analysis/chart, metrics, headers, persistence, and cleanup flows. **Result:** Both images and the full stack passed; limitations and the skipped credential-dependent LLM smoke were reported explicitly.

### 5. Account ownership isolation

**Situation:** Adding authentication only at top-level routes could leave child IDs vulnerable to cross-user access. **Task:** Apply one authorization boundary to all dataset-derived resources. **Action:** Introduced users/owners and made every child service resolve its parent through an owner-scoped repository, returning 404 for foreign IDs; added auth and isolation tests. **Result:** Dataset, Profile, Query, Analysis, Chart, Agent, and Report share consistent ownership semantics in API tests and Compose smoke verification.

## Future extension discussion

For scale, separate synchronous HTTP orchestration from durable jobs, add Redis-backed limits, object storage, cancellation/idempotency, centralized traces, and stronger worker isolation. Preserve the existing typed tool boundary rather than expanding model authority. For product quality, add browser E2E, adversarial/fuzz testing, measured performance baselines, and real-provider evals with redacted fixtures.
