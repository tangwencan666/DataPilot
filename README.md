# DataPilot — AI 智能数据分析 Agent 平台

**Current Stage: Stage 7 — Planner Agent Foundation**

DataPilot 当前提供结构化数据集的上传、持久化、列表、详情、预览和删除能力。PostgreSQL 保存 Dataset 元数据，原始 CSV/XLSX 文件保存在项目管理的上传目录中。

## 已实现

- CSV 与 XLSX 上传、验证和解析
- Dataset PostgreSQL 元数据持久化
- Dataset 分页列表、详情、限量预览和删除
- 删除元数据时同步清理磁盘文件
- Excel 默认分析第一个 worksheet，并记录所有 sheet 名和当前选择
- React Dataset List / Dataset Detail 界面
- SQLAlchemy 2.x、psycopg 与 Alembic migration
- 确定性 Data Profiling 与 Data Quality Score
- Numeric、Categorical、Text、Datetime、Boolean 列画像
- 缺失、重复、常量、高基数、异常值和无限值质量规则
- 受限 Pearson Correlation Analysis
- Profile 持久化、显式生成与刷新
- Natural Language Questions 与 OpenAI-compatible LLM Provider
- Structured Output SQL generation 与 Generated SQL transparency
- sqlglot AST Safe SQL Validation
- DuckDB CSV/XLSX Query Execution
- Analysis Query History
- Structured Python Analysis Tool（Controlled Pandas Operations）
- 强类型 Operation Pipeline、Analysis History 与 Execution Trace
- GroupBy、Filtering、Sorting、Correlation、Value Counts、Descriptive Statistics、Time Series 与 Derived Columns
- Structured Chart Tool：Bar、Line、Area、Pie、Scatter、Histogram 与 Boxplot
- 后端聚合、时间分桶、统计、确定性采样与安全 ECharts option 生成
- Charts Tab、Create Chart、Chart Gallery、Chart Detail 与 Chart 持久化
- Planner Agent、严格 Structured AgentPlan 与 DAG validation
- SQL / Analysis / Chart Tool Registry 与顺序执行轨迹
- AgentRun / AgentStepRun 历史、Artifact 引用与结构化 Final Synthesis
- Dataset Detail AI Analyst、Plan UI、Step Details 与 Final Answer

Stage 7 已提供一次性 Plan-then-Execute Planner Agent。它不是无限 ReAct loop、self-correcting Agent 或 Multi-Agent system，也没有 Report Agent。

## 项目结构

```text
D:\毕业项目二
├── backend
│   ├── alembic\versions
│   ├── app
│   │   ├── api.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── parsers.py
│   │   ├── profiling
│   │   ├── profile_service.py
│   │   ├── query
│   │   ├── analysis
│   │   ├── charts
│   │   ├── agents
│   │   ├── repositories.py
│   │   └── services.py
│   ├── data\uploads
│   └── tests
├── frontend\src
│   ├── api
│   └── App.tsx
├── .env.example
└── docker-compose.yml
```

## 环境准备

复制环境变量示例：

```powershell
Set-Location 'D:\毕业项目二'
Copy-Item .env.example backend\.env
```

默认连接：

```dotenv
DATABASE_URL=postgresql+psycopg://datapilot:datapilot@localhost:5432/datapilot
MAX_UPLOAD_MB=20
PREVIEW_ROW_LIMIT=20
PROFILE_MAX_ROWS=100000
PROFILE_SAMPLE_ROWS=50000
PROFILE_TOP_VALUES=10
LLM_API_KEY=
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=
QUERY_DEFAULT_LIMIT=100
QUERY_MAX_LIMIT=1000
QUERY_TIMEOUT_SECONDS=10
ANALYSIS_MAX_ROWS=200000
ANALYSIS_SAMPLE_ROWS=50000
ANALYSIS_MAX_RESULT_ROWS=1000
ANALYSIS_MAX_RESULT_CELLS=100000
ANALYSIS_MAX_OPERATIONS=10
ANALYSIS_MAX_COLUMNS=50
ANALYSIS_MAX_GROUPBY_COLUMNS=3
ANALYSIS_MAX_METRICS=10
ANALYSIS_MAX_SORT_COLUMNS=3
ANALYSIS_TIMEOUT_SECONDS=15
ANALYSIS_MAX_TOP_VALUES=100
CHART_MAX_POINTS=5000
CHART_MAX_SERIES=20
CHART_MAX_CATEGORIES=100
CHART_MAX_PIE_SLICES=12
CHART_MAX_HISTOGRAM_BINS=100
CHART_MAX_TITLE_LENGTH=200
CHART_MAX_OPTION_BYTES=1000000
CHART_MAX_RESULT_ROWS=5000
AGENT_MAX_STEPS=8
AGENT_MAX_CONTEXT_COLUMNS=100
AGENT_MAX_CONTEXT_CHARS=30000
AGENT_MAX_INTERMEDIATE_ROWS=100
AGENT_MAX_INTERMEDIATE_CELLS=5000
AGENT_MAX_FINAL_FINDINGS=10
AGENT_TIMEOUT_SECONDS=60
UPLOAD_DIR=data/uploads
```

示例凭据仅供本地开发，不应作为生产凭据。

## PostgreSQL 与迁移

使用 Docker 启动本地 PostgreSQL：

```powershell
Set-Location 'D:\毕业项目二'
docker compose up -d postgres
```

执行 migration：

```powershell
Set-Location 'D:\毕业项目二\backend'
.\.venv\Scripts\Activate.ps1
alembic upgrade head
```

应用不会使用 `create_all` 代替 migration。AgentRun / AgentStepRun migration 为 `20260830_0006`。

## 启动后端

```powershell
Set-Location 'D:\毕业项目二\backend'
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000
```

API 文档：http://localhost:8000/docs

## 启动前端

```powershell
Set-Location 'D:\毕业项目二\frontend'
npm install
npm run dev
```

前端地址：http://localhost:5173

## Dataset API

- `POST /api/v1/datasets`：上传 CSV/XLSX
- `GET /api/v1/datasets?page=1&page_size=20`：分页列表，按创建时间倒序
- `GET /api/v1/datasets/{dataset_id}`：Dataset 详情
- `GET /api/v1/datasets/{dataset_id}/preview`：字段统计与限量数据预览
- `POST /api/v1/datasets/{dataset_id}/profile`：生成或刷新数据画像
- `GET /api/v1/datasets/{dataset_id}/profile`：查询已持久化画像，不会自动生成
- `POST /api/v1/datasets/{dataset_id}/queries`：自然语言问题生成、验证并执行 SQL
- `GET /api/v1/datasets/{dataset_id}/queries`：分页 Query History
- `GET /api/v1/datasets/{dataset_id}/queries/{query_id}`：Query metadata
- `POST /api/v1/datasets/{dataset_id}/analyses`：执行强类型结构化 AnalysisPlan
- `GET /api/v1/datasets/{dataset_id}/analyses`：分页 Analysis History
- `GET /api/v1/datasets/{dataset_id}/analyses/{analysis_id}`：Analysis metadata
- `POST /api/v1/datasets/{dataset_id}/charts`：验证 ChartSpec、准备数据、生成并保存图表
- `GET /api/v1/datasets/{dataset_id}/charts`：分页 Chart Gallery
- `GET /api/v1/datasets/{dataset_id}/charts/{chart_id}`：Chart metadata 与安全 option
- `DELETE /api/v1/datasets/{dataset_id}/charts/{chart_id}`：删除图表记录
- `POST /api/v1/datasets/{dataset_id}/agent-runs`：规划、验证并执行一次 Agent Run
- `GET /api/v1/datasets/{dataset_id}/agent-runs`：分页 Agent History
- `GET /api/v1/datasets/{dataset_id}/agent-runs/{agent_run_id}`：Agent Run、Steps 与 Artifacts
- `DELETE /api/v1/datasets/{dataset_id}`：删除元数据与磁盘文件
- `GET /api/v1/health`：服务健康检查

## 测试与构建

测试使用临时 SQLite 数据库与临时上传目录，不依赖开发机已有数据；生产运行仍使用 PostgreSQL。

```powershell
Set-Location 'D:\毕业项目二\backend'
.\.venv\Scripts\python.exe -m pytest

Set-Location 'D:\毕业项目二\frontend'
npm run build
```

## 文件安全

- 仅允许 `.csv` 与 `.xlsx`，不支持 `.xls`
- 同时检查扩展名和允许的 MIME 类型
- 文件大小由 `MAX_UPLOAD_MB` 控制
- 磁盘文件名使用 UUID，不使用用户文件名
- 用户文件名先提取 basename，写入前验证目标仍在 uploads 目录
- 解析或数据库写入失败会清理不完整文件
- 真实上传内容已由 `.gitignore` 排除

## Profiling 与质量评分

画像只读取 Dataset 记录对应的受管文件，不接受任意文件路径。每次生成只加载一次文件；超过 `PROFILE_MAX_ROWS` 时，使用固定 `random_state=42` 的可复现样本，并在结果中记录 `is_sampled`、`sampled_row_count`、`source_row_count` 和统计范围。

质量分从 100 开始，使用确定性扣分：

- 缺失比例最多影响 30 分
- 重复比例最多影响 20 分
- 每个全空字段扣 10 分，最多 30 分
- 每个常量字段扣 2 分，最多 10 分
- ERROR 问题扣 5 分、WARNING 问题扣 2 分，问题项合计最多扣 20 分
- 最终分数限制在 0–100

相关性仅针对非恒定 Numeric 字段计算 Pearson correlation；列数、阈值和最大返回 pair 数均由配置限制。

## Natural Language SQL 安全模型

调用链为 `Question → bounded schema context → LLM structured SQL candidate → sqlglot AST validation → DuckDB execution → structured result`。LLM 不能连接数据库，也不能获得磁盘路径或完整数据文件。

- 只允许单条 SELECT/CTE Query，且必须读取逻辑表 `dataset`
- 拒绝数据修改、DDL、ATTACH/COPY/PRAGMA/INSTALL/LOAD/CALL 等命令
- 拒绝系统目录、其他表、文件读取、网络读取和外部数据库 scan functions
- Validator 自动加入或收紧 LIMIT；结果另受最大单元格数限制
- DuckDB 使用独立内存 connection；CSV 使用受管路径创建 relation，XLSX 通过 pandas 注册 DataFrame
- worker thread 执行并在超时时调用 DuckDB `interrupt()`；超时不是仅配置未使用
- NaN、Infinity、Timestamp、Decimal 和 NumPy scalar 转换为稳定 JSON 值
- Query History 只保存 metadata，不保存巨大结果集

如果 `LLM_API_KEY` 或 `LLM_MODEL` 未配置，旧功能仍正常启动和使用；只有 Query API 返回 `503 / LLM_NOT_CONFIGURED`。API Key 必须只保存在服务端环境变量中。

## Controlled Python Analysis

Stage 5 使用 Pydantic discriminated-union 定义的 Operation DSL，而不是 Python 源代码。API 没有 `code`、`expression`、`file_path` 或 URL 输入，也没有调用 `exec`、`eval`、`df.query(user_string)`、任意函数或 module import。

支持的操作：`summarize`、`groupby_aggregate`、`filter_rows`、`sort_rows`、`correlation`、`value_counts`、`descriptive_statistics`、`time_series_aggregate`、`derive_column` 和 `top_n`。Filter、aggregation、frequency、sort direction 与 derived arithmetic 均为 allowlist Enum，可按顺序组成有限 pipeline。

父进程负责 Dataset lookup、路径边界、计划验证、超时和 AnalysisRun 持久化。纯 worker 只接收受管路径、文件类型、已验证 plan 和数值限制，通过 Windows-compatible `multiprocessing.get_context("spawn")` 启动。超时会先 `terminate()`，必要时 `kill()`，数据库对象、FastAPI Request、Session 和 LLM Provider 不进入子进程。

大数据策略不会偷偷产生错误全量结论：仅 descriptive/correlation 允许确定性 sample；涉及 SUM、GroupBy、Filter 等全量操作会返回 `ANALYSIS_DATASET_TOO_LARGE`。超大 XLSX 因读取前无法低成本抽样而直接拒绝。结果行数和 cells 会安全截断，并明确 `truncated`。

当前保护是结构化能力限制、进程隔离和应用级资源上限，不是完整 OS/container memory sandbox。生产级 arbitrary Python 必须放入独立 container 或 microVM，并配置 OS resource quotas。

## Structured Chart Tool 与 ECharts 安全

Chart 创建链路为 `Structured ChartSpec → Pydantic discriminated-union validation → server-side data preparation → safe option builder → ECharts rendering`。当前来源为可复现的 `DATASET` specification；Stage 4/5 没有持久化完整结果，因此不会伪装成可重建任意历史 Query/Analysis 结果。

后端完成 grouping、allowlist aggregation、sorting、limit、date bucketing、histogram 和 boxplot 统计。前端只渲染已验证 option，不执行聚合。Scatter 超过 5000 点时用 `random_state=42` 确定性采样并记录源点数、渲染点数和 sampled；Bar/Line 优先完整聚合，不以抽样改变统计结论。Series、category、pie slice、histogram bin、title、结果规模与 option bytes 均有配置上限。

模型或用户不能提交 raw ECharts option。Schema 使用 `extra=forbid`，Option Builder 只产生 title、tooltip、legend、grid、axes 和内建 bar/line/pie/scatter/boxplot series；不接受 `eval`、`new Function`、callback、formatter function string、HTML、script、custom renderer 或任意 JavaScript。未来正确链路仍是 `LLM output → ChartSpec → validation → Safe Option Builder`，而不是 `LLM → raw JavaScript`。

## Planner Agent Foundation

```text
User Question
  ↓
Bounded Dataset/Profile Context
  ↓
Planner → Structured AgentPlan → DAG / schema / column validation
  ↓
Tool Registry
  ├─ SQL Tool → Stage 4 SQL generator → sqlglot validator → DuckDB
  ├─ Analysis Tool → Stage 5 AnalysisPlan → isolated controlled executor
  └─ Chart Tool → Stage 6 ChartSpec → safe option builder
  ↓
Bounded Execution Trace → Structured Final Synthesizer
```

Planner 只获得 Dataset 名称与规模、确定性截断的字段/画像摘要、质量问题、相关性以及 Tool 能力说明；不会获得完整数据、受管文件路径、数据库连接、API Key 或 Authorization header。默认最多 100 个 context columns、每列 3 个 sample values、20 个质量问题、20 个 correlations 和 30000 字符，并记录 `context_truncated` metadata。

AgentPlan 是严格 tool-specific discriminated union。SQL step 只能提交自然语言子问题，不能提交 SQL；Analysis 和 Chart step 必须分别通过原有 DSL。Validator 检查最大 8 步、唯一 id、只引用先前步骤的依赖、DAG、字段存在性、基础语义类型及 code/path/network injection。Runtime 只从显式 Registry 获取 SQL/Analysis/Chart adapter，没有 shell、file、browser、HTTP 或 arbitrary Python tool，也没有 `unsafe` / `skip_validation` / `trusted_agent` 绕过入口。

Runtime 只执行一次完整计划，不在 observation 后调用 LLM 重新规划。失败步骤的 dependents 标记为 `SKIPPED`，独立步骤仍可运行；有有效结果时为 `PARTIAL`，没有有效结果时为 `FAILED`。总 deadline 为 60 秒且只在步骤间启动检查，正在运行的 SQL/Analysis Tool 继续受各自 timeout 控制。中间结果最多保留 100 rows / 5000 cells，数据库只保存受限摘要和 artifact id，不保存巨大结果或 chain-of-thought。

Final Synthesizer 只接收原始问题、planner summary 和受限 step summaries，输出 `answer`、`key_findings`、`limitations`、`used_tools` 与 artifacts。日志记录 run/dataset/step/tool/status/duration，不记录 secrets 或完整 Dataset。未配置 LLM 时只有 Agent API 返回 `AGENT_LLM_NOT_CONFIGURED`，Stage 1–6 功能保持可用。

## 当前限制

- 同步解析，状态模型已为未来异步处理预留 `UPLOADING / PROCESSING / READY / FAILED`
- Profiling 当前同步执行，Profile 状态已预留 `PENDING / RUNNING / READY / FAILED`
- NL→SQL 当前为单次生成，没有自动重试、Agent loop 或多轮会话
- Analysis worker 当前没有 OS-level memory quota，XLSX sampling 能力有限
- XLSX 固定使用第一个 worksheet
- CSV 当前按 UTF-8 解析
- 数据文件保存在本机磁盘，尚无对象存储
- 下一阶段规划为 **Stage 6 — Chart & Visualization Tool**
