# Resume Project Description

## 中文精简版（80–120 字）

DataPilot 是面向结构化数据的 AI 分析 Agent 平台。系统以 FastAPI、React、PostgreSQL 和 DuckDB 构建，通过 sqlglot AST 校验、结构化分析/图表 DSL、受限 Planner 与证据引用报告，将 LLM 输出置于程序校验之后；已完成 Docker Compose 实栈验证、9 个 Alembic 迁移及 249 项后端、6 项前端测试。

## 中文详细版（150–250 字）

独立设计并实现 DataPilot 结构化数据分析 Agent 平台，覆盖 CSV/XLSX 管理、数据画像与质量检测、自然语言 SQL、受控 Pandas 分析、ECharts 可视化、Planner 执行轨迹、受限观察/修复及证据驱动报告。针对 LLM 不可信输出，使用 sqlglot 进行 SQL AST 白名单校验，以 Pydantic 判别联合定义 Analysis/Chart DSL，通过 spawn 子进程和超时限制隔离分析，并对 Agent 计划执行最大步数、DAG、工具与字段校验。平台实现 JWT、Argon2、资源归属隔离、限流、配额、请求 ID 和指标；使用 PostgreSQL 16、Alembic 与 Docker Compose 完成真实迁移及发布验证，并以 249 项后端、6 项前端测试和 CI 质量门禁保障回归。

### 中文成果要点

- 将 SQL、Analysis、Chart 三类模型输出统一置于强类型 Schema、白名单与资源限制之后，禁止任意代码和 raw JavaScript。
- 设计最多 8 步的计划 DAG 与确定性修复策略，保留步骤、Attempt、Observation 和 Artifact 审计轨迹。
- 以 evidence refs 约束报告洞察，使用程序模板生成并转义 Markdown/HTML。
- 完成 9 个 Alembic 迁移、PostgreSQL 16.15 实库 round-trip 和 Docker Compose 全链路验证。
- 建立 249 项后端与 6 项前端测试，以及 Ruff、ESLint、TypeScript、Vite CI 门禁。

## English short version

Built DataPilot, a structured-data analysis agent using FastAPI, React, PostgreSQL, and DuckDB. Placed untrusted LLM output behind `sqlglot` AST validation, typed analysis/chart DSLs, a bounded planner and evidence-reference checks. Verified nine Alembic revisions on PostgreSQL 16.15 and maintained 249 backend plus 6 frontend tests.

## English detailed version

Designed and implemented DataPilot, an inspectable analysis platform covering CSV/XLSX management, deterministic profiling and quality checks, natural-language SQL, controlled dataframe operations, safe ECharts visualizations, bounded agent planning/repair, and evidence-backed reports. Treated model output as untrusted by combining Pydantic discriminated unions, `sqlglot` AST allowlists, a spawned analysis worker, time/result limits, DAG and column validation, and program-owned report rendering. Added JWT/Argon2 authentication, owner-scoped resources, quotas, request IDs, metrics, Docker Compose, PostgreSQL migrations, and CI quality gates. Verified the nine-revision Alembic chain and round-trip against PostgreSQL 16.15 with 249 backend and 6 frontend automated tests.

### English achievements

- Built typed SQL/analysis/chart execution boundaries that reject arbitrary code, external readers, and raw JavaScript.
- Implemented an eight-step bounded plan DAG with deterministic, same-tool repair and persisted execution evidence.
- Grounded report insights in validated evidence references and escaped application templates.
- Verified nine Alembic revisions and the complete Compose flow on PostgreSQL 16.15.
- Enforced regression gates with 249 backend tests, 6 frontend tests, Ruff, ESLint, TypeScript, and Vite.
