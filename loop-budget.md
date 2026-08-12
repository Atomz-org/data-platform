# Loop Budget

Daily ceiling across all loops: **200,000 tokens**. The circuit breaker in
`pf.loops.runner` opens on depletion and on 3 consecutive failures of the same
loop, counted in `loop-ledger.json` so a restart does not reset the count.

| Loop | Budget/run | Model | Effort | Rationale |
|---|---:|---|---|---|
| `freshness-triage` | 4,000 | haiku-4-5 | — | Reads monitor rows; mechanical |
| `test-failure-triage` | 12,000 | opus-5 | medium | Needs reasoning over lineage |
| `metric-gap-harvester` | 8,000 | sonnet-5 | low | Structured, narrow |
| `pii-audit` | 0 | — | — | Pure graph query, no model call |
| `impact-sentinel` | 0 | — | — | Pure graph query, no model call |
| `index-refresher` | 0 | — | — | Deterministic rebuild |

Three of six loops cost nothing: they are graph queries, not model calls. That is
the point of building the index — the cheapest agent work is the work an agent
does not have to do.

Spend is recorded per run in `loop-ledger.json` and per agent in
`data/_platform.duckdb` (`agent_runs`), and charted in the control-plane UI.
Verify prompt caching is working via `cache_read_tokens` — if it is zero across
repeated runs, a volatile prefix is defeating it.
