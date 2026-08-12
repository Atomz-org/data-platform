---
name: optimize-performance
description: Diagnose and tune a slow dlt pipeline.
---
# Pipeline performance

Diagnose before tuning — read `get_local_pipeline_state` and the load timings.

| Symptom | Lever |
|---|---|
| Slow extract, API-bound | `parallelized=True` on the resource; raise `workers` |
| Slow extract, one big table | partition the resource by date and fan out |
| High memory | lower `buffer_max_items`; enable file rotation (`file_max_items`) |
| Slow normalize | `LOADER_FILE_FORMAT=parquet`; raise normalize `workers` |
| Slow load | raise `load.workers`; batch smaller with `file_max_bytes` |
| Full reload every run | missing `incremental` — this is the usual answer |

Never raise concurrency past the project's DuckDB writer pool; the pool exists
so sister projects stay parallel.
