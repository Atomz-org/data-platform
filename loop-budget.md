# Loop Budget

Daily ceiling across all loops: **200,000 tokens**. The circuit breaker in
`pf.loops.runner` opens on depletion and on 3 consecutive failures of the same
loop, counted in `loop-ledger.json` so a restart does not reset the count.

| Loop | Budget/run | Model | Effort | Cache | Rationale |
|---|---:|---|---|---|---|
| `freshness-triage` | 4,000 | haiku-4-5 | n/a | none | Reads monitor rows; mechanical |
| `test-failure-triage` | 12,000 | opus-5 | medium | 5m | Needs reasoning over lineage |
| `metric-gap-harvester` | 8,000 | sonnet-5 | low | 5m | Structured, narrow |
| `pii-audit` | 0 | — | — | Pure graph query, no model call |
| `impact-sentinel` | 0 | — | — | Pure graph query, no model call |
| `index-refresher` | 0 | — | — | Deterministic rebuild |

Three of six loops cost nothing: they are graph queries, not model calls. That is
the point of building the index — the cheapest agent work is the work an agent
does not have to do.

## Why the Effort and Cache columns are not free choices

Both are per-model constraints, enforced in `pf.agents.models` and checked by
`pf models`:

- **Effort is `n/a` on Haiku 4.5** because that model *rejects*
  `output_config.effort` outright — the request 400s. Routing declares the
  intent anyway; the renderer drops it for models that cannot take it.
- **Caching has a per-model minimum prefix** (512 tokens on Opus 5, 1024 on
  Sonnet 5, 4096 on Haiku 4.5) and it is not monotonic across generations. The
  shared prefix here is ~1,165 tokens: it caches on Opus and Sonnet and can
  never cache on Haiku, so no marker is sent there rather than implying one
  works.
- **TTL comes from cadence.** A 1h entry bills its write at 2x and needs ~3
  reads to pay for itself, so only a loop running more often than hourly asks
  for one. `freshness-triage` runs every 2h — a 1h TTL would expire before it
  came back, paying the premium for zero reads.

Spend is recorded per run in `loop-ledger.json` and per agent in
`data/_platform.duckdb` (`agent_runs`), and charted in the control-plane UI.
Verify prompt caching is working via `cache_read_tokens` — if it is zero across
repeated runs on Opus or Sonnet, a volatile prefix is defeating it. Zero on
Haiku is expected, not a bug.
