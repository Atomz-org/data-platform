---
name: create-rest-pipeline
description: Ingest from a REST API with dlt Core — a declarative rest_api source first, RESTClient only for a shape it cannot express.
---
# REST API pipeline

Use `dlt.sources.rest_api` before writing any request code. Decisions to make
explicitly:

- **Client** — `base_url`, headers (public feeds often answer 429 without a
  User-Agent), auth through `secrets_update_fragment`, never inline.
- **Resources** — one endpoint each. A list the endpoint is called once per
  (symbols, accounts) is a parent resource with `selected: False` that yields
  the whole list as one page; the child binds it with
  `params: {x: {type: resolve, resource: <parent>, field: <key>}}` and carries
  the parent's key with `include_from_parent`. A dependent resource iterates
  what its parent yields, so yield the list — one dict per yield is iterated
  as its keys.
- **Pagination** — name the paginator (`json_link`, `offset`, `page_number`,
  `cursor`, `header_link`). Detection is for exploring, not for a source of record.
- **Incremental** — `incremental` with a `start_param`, a `cursor_path` and a
  `lag` for late corrections. It is one cursor per resource: when the window is
  per key (one series per symbol), keep a cursor per key in
  `dlt.current.resource_state()` instead. State syncs with the destination and
  is dropped when the dataset is gone, so a wiped warehouse rebackfills.
- **Shape** — `processing_steps` (`filter`, `map`, `yield_map`) reshape rows in
  flight. Parallel arrays (`timestamp[]` beside `close[]`) are the case for
  `RESTClient` and a Python parser, not for a selector. Say why in the module.
- **Write** — `merge` with `primary_key` for series that revise, `append` for
  immutable events, `replace` for a catalog. Type hints in `columns` for every
  column dlt would otherwise infer from the first page.
- **Contract** — the platform applies `DEFAULT_CONTRACT` (`data_type: freeze`).
  Tighten to `STRICT_CONTRACT` per source; never loosen.
- **Failure isolation** — a backup feed ignores 429 and 5xx per request through
  `response_actions`; a source of record raises when every request failed.
- **Verify** — `run_source` returns `rows` per table; a load that left a table
  empty is red, not done. `debug-pipeline` reads the trace.

Annotate every resource before finishing: `@annotate(...)` on a function,
`annotate(...)(resource)` on one dlt generated from config. The raw dataset is
named after the source, and that is exactly what generated dbt staging reads.
