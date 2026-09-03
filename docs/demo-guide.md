# DataPilot Demo Guide

This script fits a 5–8 minute graduation defense or portfolio walkthrough. Use only the synthetic `demo/sales_demo.csv` data.

## Before the demo

1. Copy `.env.example` to `.env`, replace local secrets, and optionally configure an LLM provider.
2. Run `docker compose up --build` and wait for PostgreSQL, backend, and frontend health checks.
3. Open `http://localhost`, register a disposable local account, and keep the API docs closed unless asked.
4. Verify the demo file still has the fields `date`, `region`, `product`, `category`, `sales`, `quantity`, and `profit`.

## Main path

1. **Login (30s):** explain that JWT authentication and owner-scoped repositories isolate datasets and their child resources.
2. **Upload (30s):** upload `demo/sales_demo.csv`; point out type, size, quota, and managed-path checks.
3. **Preview (30s):** show the real rows and fields without claiming hidden data or results.
4. **Profile and quality (45s):** generate a profile; show semantic types, ranges, values, quality score, and correlation summary.
5. **Structured analysis (45s):** group by `region`, aggregate `sales` and `profit`, then show the operation trace. Emphasize that the API accepts a DSL, not Python code.
6. **Chart (30s):** create a region-sales bar chart; explain server-side aggregation and safe ECharts option construction.
7. **AI Analyst (90s, LLM configured):** ask question 8 from the question list. Show goal, plan, dependencies, tool allowlist, live step status, attempt/observation metadata, and final answer.
8. **Report (45s):** generate a report from the completed run. Open findings, evidence references, limitations, and HTML/Markdown export.
9. **Security close (45s):** summarize SQL AST validation, analysis DSL/process isolation, chart DSL, bounded repair, evidence validation, and ownership. State clearly that the LLM is not a security boundary.

## No-LLM demo path

If the provider is unavailable, do not improvise fake agent output. Demonstrate upload, preview, profile, data quality, structured analysis, chart creation, history, authentication, and the architecture/security documents. Show that LLM-dependent APIs fail explicitly while non-LLM features remain healthy. This still demonstrates the core engineering boundary: deterministic tools are independently usable and safe.

## Recovery notes

- Port 5432 occupied: set a free `POSTGRES_PORT` in `.env` and restart Compose.
- Old demo state: delete the demo dataset through the UI and upload it again; do not delete volumes during a live defense unless necessary.
- Agent failure: expand the failed step and explain its structured observation; controlled repair is bounded and intentionally may stop.
- Never display `.env`, Authorization headers, provider dashboards, or real account data on screen.
