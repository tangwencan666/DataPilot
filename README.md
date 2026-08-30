# DataPilot — AI 智能数据分析 Agent 平台

**Current Stage: Stage 2 — Dataset Management & Persistent Data Layer**

DataPilot 当前提供结构化数据集的上传、持久化、列表、详情、预览和删除能力。PostgreSQL 保存 Dataset 元数据，原始 CSV/XLSX 文件保存在项目管理的上传目录中。

## 已实现

- CSV 与 XLSX 上传、验证和解析
- Dataset PostgreSQL 元数据持久化
- Dataset 分页列表、详情、限量预览和删除
- 删除元数据时同步清理磁盘文件
- Excel 默认分析第一个 worksheet，并记录所有 sheet 名和当前选择
- React Dataset List / Dataset Detail 界面
- SQLAlchemy 2.x、psycopg 与 Alembic migration

当前尚未实现 LLM、自然语言 SQL、Agent、Python Sandbox、Chart Agent 或 Report Agent。

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

应用不会使用 `create_all` 代替 migration。首次 migration revision 为 `20260830_0001`。

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

## 当前限制

- 同步解析，状态模型已为未来异步处理预留 `UPLOADING / PROCESSING / READY / FAILED`
- XLSX 固定使用第一个 worksheet
- CSV 当前按 UTF-8 解析
- 数据文件保存在本机磁盘，尚无对象存储
- 下一阶段规划为 **Stage 3 — Data Profiling**
