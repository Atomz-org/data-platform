---
name: create-filesystem-pipeline
description: Load CSV, Parquet, JSONL from local disk, S3, GCS or Azure.
---
# Filesystem pipeline

1. Profile first with `read-file` (duckdb-ops) — column names, types, null rates,
   row count. Do not guess the schema.
2. Use the `filesystem` source with an explicit `file_glob`.
3. Choose the reader transformer: `read_csv` (duckdb-backed), `read_parquet`,
   `read_jsonl`.
4. Set `incremental` on `modification_date` for landing zones that accumulate.
5. Credentials for cloud storage go through `secrets_update_fragment` only.
6. Annotate, then `validate_annotations`.
