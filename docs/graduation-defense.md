# Graduation Defense Guide

## 30 秒项目介绍

DataPilot 是一个面向 CSV/XLSX 的 AI 数据分析 Agent 平台。它不让模型直接执行代码，而是把自然语言目标转换为受限计划，再通过安全 SQL、结构化分析和图表工具执行。每一步都有校验、状态、证据和有限修复，最终报告中的洞察必须引用真实执行证据。

## 2 分钟项目介绍

系统前端使用 React，后端使用 FastAPI，PostgreSQL 保存账户、数据集元信息和分析历史，DuckDB 负责只读分析查询。上传后可生成确定性画像和质量问题，也可直接运行结构化分析或创建图表。配置 LLM 后，Planner 只生成最多 8 步的强类型计划，程序验证 DAG、工具、字段和语义，再通过 SQL、Analysis、Chart Registry 执行。SQL 经 sqlglot AST 校验；Analysis 只能使用 Pydantic DSL 并在 spawn 子进程执行；Chart 由服务端生成安全 ECharts option。失败先形成结构化 Observation，只有允许的错误能做一次同工具修复。最终报告从 AgentRun 快照提取有限证据，每个 Insight 必须引用有效 evidence ID，HTML 由程序转义模板生成。项目完成了 JWT 归属隔离、Docker Compose、9 个 Alembic 迁移及 249+6 项测试。

## 5 分钟技术介绍

1. **数据入口：** 文件扩展名、MIME、大小和配额校验；UUID 文件名和目录 containment；PostgreSQL 保存元信息。
2. **确定性能力：** Profile、Quality、Structured Analysis 和 Chart 不依赖 LLM，便于离线演示与结果复现。
3. **SQL 安全：** 模型生成结构化候选，sqlglot 解析 AST，只允许逻辑表上的单条 SELECT/CTE，再由 DuckDB 限时执行。
4. **分析安全：** 不接收 Python code；判别联合 DSL 限定操作、字段和算子，子进程承担超时隔离。
5. **Agent：** 一次规划完整 DAG，Registry 只有三种工具；运行期记录步骤、Attempt、Observation 和 Artifact。
6. **修复：** 程序分类失败并决定是否可重试，LLM 只修复原工具输入，且必须重新校验；不是无限 ReAct。
7. **证据报告：** 受限快照注册 evidence，洞察引用经验证，固定模板避免 raw HTML/JS。
8. **平台：** Argon2/JWT、owner-scoped repository、限流、配额、请求 ID、指标、Alembic、Docker 和 CI。

## 设计动机

普通聊天式分析很难证明“答案从哪里来”，也很难安全执行模型输出。本项目将可解释执行轨迹和安全边界作为主线：模型负责提出结构化意图，程序负责授权、验证、执行和证据约束。

## 常见答辩问题与参考回答

### 1. 为什么做这个项目？

因为自然语言降低了数据分析门槛，但直接让模型生成并执行 SQL/Python 风险很高。我希望验证一种“模型提议、程序裁决、结果可追溯”的工程方案。

### 2. 系统架构如何分层？

React/Nginx 是展示层，FastAPI 是 API 和业务编排层，PostgreSQL 保存身份与历史，受管 volume 保存上传文件；Profile、SQL、Analysis、Chart 是工具层，Planner/Runtime/Report 是编排与证据层。

### 3. Agent 为什么采用 Plan-then-Execute？

完整计划可提前检查最大步数、依赖、环和工具范围，也便于 UI 展示与审计。代价是适应性不如开放循环，因此只补充有限的同工具修复。

### 4. 为什么不用任意 Python `exec`？

它可访问文件、网络、进程和内存，应用级字符串过滤无法可靠限制。结构化 DSL 牺牲通用性，换取可验证、可测试和可控资源边界。

### 5. 为什么需要 sqlglot？

关键词匹配无法理解 CTE、嵌套表达式或混淆语法。AST 能按语义验证语句类型、表和函数，并统一添加/收紧 LIMIT，但仍需执行期限制作为纵深防御。

### 6. 为什么使用 DuckDB？

它适合进程内分析 CSV/DataFrame，支持标准分析 SQL，部署简单。这里使用独立内存连接和逻辑 relation，避免给模型 PostgreSQL 业务库权限。

### 7. 为什么同时使用 PostgreSQL？

PostgreSQL 负责持久化用户、归属、状态和审计历史，强调事务与约束；DuckDB 负责临时分析计算。二者职责不同。

### 8. Observation / Repair 有什么价值？

它把失败变成可持久化的类别和摘要。程序先决定是否可修复，再允许 LLM 返回同工具结构化输入，可处理列名或聚合不匹配，又避免无限循环。

### 9. 为什么不用无限 ReAct？

无限循环难以预算成本、证明终止和审计工具调用，还可能放大 prompt injection。本实现使用步数、时间和修复预算提供确定上界。

### 10. Evidence-backed Report 是什么？

报告不是把完整运行日志交给模型自由写作，而是注册有限证据。每条 insight 必须引用存在的 step/query/analysis/chart/profile evidence，未知引用会被拒绝。

### 11. 如何降低 LLM 幻觉？

强类型输出、真实工具执行、有限上下文、evidence refs 校验和 limitations 字段共同降低风险，但不能宣称消除幻觉；用户仍需判断业务解释。

### 12. 如何防止 SQL Injection 和破坏性 SQL？

业务元数据查询使用 ORM/参数化；生成 SQL 解析 AST，只允许单条 SELECT/CTE 和逻辑 `dataset`，拒绝 DDL/DML、ATTACH、COPY、外部 reader 等。

### 13. 如何实现账户隔离？

JWT 得到当前用户，每个数据集及其子资源都先通过 owner-scoped repository 查父数据集。外部用户访问同 ID 返回 404。

### 14. Docker 部署结构是什么？

Compose 包含 PostgreSQL、非 root backend 和非特权 Nginx frontend；数据库和上传分别使用持久 volume，backend 等待数据库健康并执行 Alembic 升级。

### 15. 项目最大技术难点是什么？

不是调用 LLM，而是统一三种工具安全边界、跨步骤数据引用、失败分类/修复预算，以及把报告洞察绑定到真实证据。

### 16. Pydantic 在项目中的作用？

它定义输入输出契约，尤其用 discriminated union 区分工具与操作类型，并通过 `extra=forbid` 拒绝模型夹带字段。它不是唯一安全层，后续还有语义校验。

### 17. 进程隔离是否等于安全沙箱？

不是。spawn worker 便于超时终止和故障隔离，但没有 OS memory quota、系统调用过滤或 microVM 边界，文档明确披露这一限制。

### 18. 如何验证数据库迁移？

共有 9 个不可回写旧文件的 Alembic revision。CI 使用 PostgreSQL 16，发布时还执行真实 `0001→0009`、`0009→0008→0009` round-trip 和表检查。

### 19. 没有 LLM Key 时系统会怎样？

应用正常启动，Dataset、Profile、Quality、Structured Analysis、Chart 可用；NL SQL、Agent、Report 返回明确的未配置错误，不伪造结果。

### 20. 为什么图表也需要安全 DSL？

ECharts option 可包含 formatter callback 或 custom renderer。让服务端从 `ChartSpec` 构建有限 option，可避免 raw JS 并统一点数、类别和 option 大小限制。

### 21. 当前有哪些不足？

进程内限流、同步长任务、本地上传 storage、无 OS 沙箱和恶意文件扫描；浏览器 token 使用 localStorage；真实 LLM 发布 smoke 因无凭据未执行。

### 22. 后续怎么改进？

优先是共享限流、异步队列、对象存储、容器/microVM 隔离、集中 tracing，以及可选 PDF 导出；不会先扩大 Agent 权限。

### 23. 项目有什么创新点？

更准确地说是工程组合创新：将 AST SQL、结构化分析/图表 DSL、有限 Agent 修复与证据引用报告连接成一致的“不信任模型输出”链路，而不是提出新的基础算法。

### 24. 测试覆盖了什么？

249 项后端测试覆盖 validator、工具执行、Agent、repair、report、auth/ownership 和 API；6 项前端测试覆盖关键认证/API行为，并通过 lint/type/build。数量不等于完备性，仍需性能和渗透测试。
