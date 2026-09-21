---
type: Vendor Upstream
title: DuckDB Quack
description: the client-server protocol serving every project's dev database
resource: https://github.com/duckdb/duckdb-quack
tags:
- vendor
- runtime
- MIT
status: stable
sources:
- id: duckdb-quack:README.md
  resource: https://github.com/duckdb/duckdb-quack
  title: README.md
---

# DuckDB Quack

The quack extension is what `pf quack serve` puts in front of each project's dev DuckDB file. The extension binary itself arrives at runtime via `INSTALL quack`; this pin is the reference source for the wire behaviour our runtime is built around — what `quack_serve`, `quack_query` and the client's ATTACH can and cannot carry.

## Adopted

- **README.md** (shape) -> platform/src/pf/runtime/quack.py
  Serve/secret/attach surface as documented upstream. Our runtime routes reads through `quack_query` passthrough and keeps writers on the file inside a write window, because the experimental client's ATTACH cannot carry schema DDL or schema-qualified base-table fetches — re-measure against this pin when it moves.

## Declined

