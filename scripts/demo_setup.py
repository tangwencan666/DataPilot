"""Create a non-sensitive demo CSV without invoking any LLM API."""
from pathlib import Path

CONTENT = """date,region,product,category,sales,quantity,profit
2026-01-05,East,Atlas,Software,12500,25,4100
2026-01-12,West,Beacon,Services,9800,14,2200
2026-02-04,East,Atlas,Software,11700,22,3600
2026-02-18,North,Cobalt,Hardware,14300,31,2800
2026-03-08,West,Beacon,Services,8100,12,1500
2026-03-21,North,Cobalt,Hardware,15100,34,3100
"""

target = Path(__file__).resolve().parents[1] / "demo" / "sales_demo.csv"
target.parent.mkdir(exist_ok=True)
target.write_text(CONTENT, encoding="utf-8")
print(f"Created {target}. Register in the UI and upload this file; no paid LLM call was made.")
