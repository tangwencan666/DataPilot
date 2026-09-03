# Project Highlights

## 1. AST-level SQL boundary

**Problem:** model-generated SQL cannot be trusted by keyword filtering. **Design:** parse with `sqlglot`, allow one read-only SELECT/CTE over a logical dataset relation, and reject unsafe commands/readers. **Safety:** bounded DuckDB execution and timeout remain mandatory after validation. **Trade-off:** the supported SQL surface is intentionally narrower than DuckDB.

## 2. Structured analysis instead of arbitrary Python

**Problem:** arbitrary Python creates code-execution and resource risks. **Design:** discriminated Pydantic operations cover useful dataframe workflows. **Safety:** spawn worker, timeout, row/cell/operation caps, and no code/path inputs. **Trade-off:** novel algorithms require a reviewed DSL extension.

## 3. Safe visualization DSL

**Problem:** raw ECharts options can carry JavaScript callbacks. **Design:** accept a typed `ChartSpec`, prepare data server-side, and build a small option subset. **Safety:** no raw JS, functions, HTML formatter, or custom renderer. **Trade-off:** fewer customization features.

## 4. Bounded planner and dependency DAG

**Problem:** unlimited agent loops are hard to reason about and control. **Design:** one complete plan with a maximum step count, prior-step dependencies, cycle checks, and a three-tool registry. **Safety:** runtime has no route to unregistered capabilities. **Trade-off:** complex questions may need a new user run.

## 5. Deterministic observation and repair

**Problem:** tool errors need recovery without autonomous looping. **Design:** classify a bounded observation, consult deterministic policy, and optionally request one same-tool structured repair. **Safety:** all repairs re-enter original validators and share a run budget. **Trade-off:** some recoverable cases intentionally stop.

## 6. Evidence-backed reports

**Problem:** fluent summaries can detach from executed results. **Design:** snapshot bounded artifacts, require insight `evidence_refs`, validate every reference, and render fixed templates. **Safety:** escaped HTML and no model-owned markup. **Trade-off:** report expressiveness follows captured evidence.

## 7. Uniform ownership boundary

**Problem:** checking only top-level dataset routes leaves indirect-object access paths. **Design:** every child service resolves its parent through an owner-scoped repository. **Safety:** foreign IDs return 404 consistently. **Trade-off:** legacy ownerless records need migration policy.

## 8. Bounded context and persistence

**Problem:** full profiles/results leak data and exceed model budgets. **Design:** deterministic context truncation and standardized result summaries. **Safety:** no file paths, credentials, full datasets, or chain-of-thought in prompts/history. **Trade-off:** truncation can omit useful long-tail context.

## 9. Real migration and release verification

**Problem:** SQLite-only tests do not prove PostgreSQL migrations or container startup. **Design:** nine Alembic revisions, CI PostgreSQL service, real 16.15 migration/round-trip, Compose smoke, persistence, and cleanup checks. **Safety:** startup uses Alembic rather than implicit schema creation. **Trade-off:** operational scale and failover remain untested.

## 10. Honest deployment foundation

**Problem:** portfolio projects often overclaim production readiness. **Design:** document verified Docker, auth, metrics, headers, limits, and known gaps. **Safety:** limitations call out local storage, process-local rate limits, and lack of OS sandbox/malware scanning. **Trade-off:** stronger infrastructure is deferred instead of simulated.
