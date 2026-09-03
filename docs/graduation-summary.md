# Graduation Project Summary

## 题目建议

《面向结构化数据的安全可控 AI 数据分析 Agent 平台设计与实现》

## 摘要草稿

自然语言大模型降低了数据分析的交互门槛，但模型输出具有不确定性，直接执行其生成的 SQL、Python 或可视化代码会带来数据破坏、任意代码执行、资源耗尽和结论不可追溯等风险。本文设计并实现 DataPilot，一套面向 CSV/XLSX 结构化数据的可控分析 Agent 平台。系统以 React 和 FastAPI 构建交互与服务层，使用 PostgreSQL 持久化身份、数据集元信息和执行历史，使用 DuckDB 与受限 pandas worker 完成分析计算。平台将模型定位为结构化计划与洞察的提议者，通过 SQL AST 白名单、Analysis/Chart DSL、计划 DAG、工具注册表、资源限制、有限 Observation/Repair 以及 Evidence Reference 校验，由程序掌握最终授权和执行。系统同时实现数据画像、质量检测、JWT 认证、账户归属隔离、指标、Docker Compose 部署和 Alembic 迁移。测试与真实容器验证表明各核心链路能够按既定安全边界执行；本文不将其表述为 OS 级沙箱或企业级多租户系统，并讨论了分布式限流、异步任务、对象存储和更强隔离等后续方向。

## 关键词

大语言模型；数据分析 Agent；结构化输出；SQL AST；安全执行；证据追踪

## 研究背景

- 传统 BI/代码分析存在使用门槛，自然语言可改善交互。
- LLM 能生成分析意图，但文本输出不能直接获得执行权限。
- 论文重点不是训练新模型，而是研究安全、可解释、可验证的应用编排。

## 需求分析

### 功能需求

数据集上传与管理、预览、画像与质量、SQL 分析、结构化分析、图表、Agent 计划执行、观察/修复、报告、历史和导出。

### 非功能需求

输入/输出强类型、结果与上下文有界、账户隔离、失败可审计、可迁移部署、无 LLM 降级可用、测试可重复。

## 系统设计

前端负责数据工作区和执行轨迹展示；FastAPI 负责编排、认证、授权和验证；PostgreSQL 负责持久状态；受管存储保存原始文件；DuckDB、Analysis Worker 和 Chart Builder 构成工具层；Planner/Runtime/Report 构成受限 Agent 层。

## 关键技术

- Pydantic discriminated union 定义计划、工具、操作和报告契约。
- `sqlglot` 对生成 SQL 做 AST 级语义白名单校验。
- DuckDB 以内存连接执行受限只读分析。
- pandas 操作 DSL 与 spawn worker 提供有限计算能力和超时隔离。
- ECharts 安全 option builder 避免模型生成 raw JavaScript。
- DAG、Tool Registry、Observation 分类和确定性 Repair Policy 约束 Agent。
- Evidence Registry 和 `evidence_refs` 连接执行结果与报告洞察。

## 安全设计

采用纵深防御：模型上下文去敏与截断、Schema 校验、语义校验、工具白名单、资源/时间限制、所有权校验、结果截断、固定模板转义和最小化日志。明确区分应用级控制与 OS 沙箱能力。

## 系统实现

实现 Upload → Profile → Query/Analysis/Chart → Planner → Runtime → Observation/Repair → Synthesis → Report 的完整链路。数据库通过 9 个 Alembic revision 演进；Compose 启动 PostgreSQL、backend 和 frontend，并持久化元数据与上传文件。

## 测试方案

- 后端单元/API 测试：249 项，覆盖 validator、工具、Agent、Report、Auth、Ownership 和异常路径。
- 前端测试：6 项，配合 ESLint、TypeScript 和生产构建。
- CI：PostgreSQL service、迁移、Ruff、pytest、前端测试/构建。
- 发布验证：真实 PostgreSQL 16.15 migration/round-trip、Compose、HTTP smoke、持久化与清理。

不要从测试数量推导覆盖率百分比或性能结论；论文如需性能实验，应另行定义硬件、数据规模、重复次数和统计方法。

## 部署验证

已验证 backend/frontend 镜像构建、数据库健康依赖、Alembic `0001→0009`、`0009→0008→0009`、认证、账户隔离、数据集/画像/分析/图表、metrics、request ID、security headers、volume persistence 和 delete cleanup。真实 LLM smoke 因未配置凭据而跳过。

## 可陈述的创新点

1. 将 SQL AST、Analysis/Chart DSL 和 Agent Tool Registry 统一到“不信任模型输出”的执行链。
2. 使用确定性失败分类和有限同工具 Repair，在可恢复性与终止上界间折中。
3. 通过 evidence reference validation 将报告洞察绑定到执行证据。
4. 以 UI 执行轨迹和持久化 Attempt 提升 Agent 可观察性。

这些属于应用工程与系统设计创新，不宣称提出新的模型算法。

## 不足

未进行真实 LLM release smoke、负载/渗透/浏览器 E2E；限流为进程内；任务同步；上传为本地 volume；worker 无 OS-level sandbox/memory quota；无 malware scan；token 使用 localStorage。

## 未来工作

共享限流与异步队列、对象存储、容器/microVM 隔离、集中 tracing、真实模型评测与对抗测试、可选 PDF 报告。应先增强边界和评测，再考虑扩大 Agent 能力。

## 建议论文结构

1. 绪论与相关工作
2. 需求分析与威胁模型
3. 总体架构与数据设计
4. 安全 SQL/Analysis/Chart 工具实现
5. Planner、Runtime、Repair 与 Evidence 实现
6. 认证、部署与可观察性
7. 测试设计与验证结果
8. 局限、总结与展望
