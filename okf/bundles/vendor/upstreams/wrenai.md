---
type: Vendor Upstream
title: WrenAI
description: MDL — the interchange format BI and text-to-SQL consume
resource: https://github.com/Canner/WrenAI
tags:
- vendor
- spec
- Apache-2.0-for-core/**,-CC-BY-4.0-for-docs/**
status: stable
sources:
- id: wrenai:core/wren-mdl/mdl.schema.json
  resource: https://github.com/Canner/WrenAI
  title: core/wren-mdl/mdl.schema.json
---

# WrenAI

MDL is the interchange format a BI or text-to-SQL layer can consume without being told our internals. Emitting it keeps the semantic layer portable.

## Adopted

- **core/wren-mdl/mdl.schema.json** (schema) -> platform/src/pf/projections/mdl.py
  Field names and the cardinality enum come from this file, not from memory. `layoutVersion` is an integer here — we got that wrong once by guessing, which is the reason the schema is vendored.

## Declined

- **The Wren engine, UI and AI service**
  Room is left, not taken. We emit a conformant manifest; adopting Wren means pointing it at `mdl/mdl.json`, with nothing else to change.
