# LOOP.md — loop definitions

Building blocks adapted from [loop-engineering](vendor/loop-engineering).
The patterns there are software-delivery loops; a data platform watches different
subjects — freshness, drift, metric coverage, index staleness.

Run: `pf loop list` · `pf loop run <loop> <group> <project>` · `pf loop run-all <group> <project>`
Governance: `pf loop audit` · `pf loop status` · `pf gate --paths <a,b>`

## Autonomy ladder

| Level | Meaning | Promotion rule |
|---|---|---|
| **L1** | Report only. Writes nothing. | Default for every new loop. |
| **L2** | Patches inside `gate.yaml`. | After the L1 version has run clean for weeks. |
| **L3** | Unattended. | Requires a per-loop track record in the ledger. **Nothing is L3 here.** |

## Loops

| Loop | Cadence | Level | Budget/run | Writes | Subject |
|---|---|---|---:|---|---|
| `freshness-triage` | every 2h | L1 | 4,000 | no | stale sources, volume anomalies |
| `test-failure-triage` | on dbt failure | L1 | 12,000 | no | classify failing nodes by root cause |
| `metric-gap-harvester` | daily | L1 | 8,000 | no | marts with no metric coverage |
| `pii-audit` | daily | L1 | 0 | no | PII reaching a mart unmasked |
| `impact-sentinel` | pre-commit | L1 | 0 | no | blast radius of uncommitted changes |
| `dashboard-coverage` | daily | L1 | 0 | no | metrics no page shows; pages naming metrics that do not exist |
| `vendor-drift` | weekly | L1 | 0 | no | upstreams that moved, and which of our files each implicates; repo-scoped |
| `index-refresher` | on manifest change | L2 | 0 | yes | rebuild graph + context card |

Daily budget across all loops: **200,000 tokens**. The circuit breaker opens on
depletion, or after 3 consecutive failures of the same loop.

## Group overrides

The table above is the registry: platform code, the same for every company. A
family changes what it runs in `groups/<group>/loops.yaml`, and only there. A
project has no loops file: loops watch the family's subjects once, and a
project's own knowledge reaches a loop through its `CLAUDE.md` (see below).

```yaml
version: 1
loops:
  <loop-name>:            # one of the registry names
    enabled: true|false   # default true; give a reason when false
    reason: "<why disabled>"
    cadence: "<free text>"
    token_budget: <non-negative int>
    autonomy: L1          # may only lower the registry level
    waivers:              # findings to suppress; reason is mandatory
      - node: "rpt_*"     # a node name or fnmatch glob; for pii-audit, model.column
        reason: "..."
```

| Rule | Why |
|---|---|
| Autonomy may be lowered, never raised | Promotion is a human decision made in the registry after a ledger track record. |
| A loop that writes cannot be lowered to L1 | L1 means writes nothing. Lowered, `index-refresher` would still rebuild the graph, inside the read-only `pf loop run-all` sweep. Disable it instead. |
| A waiver needs a reason | A silenced finding with no stated reason is a monitor nobody acts on. |
| A disabled loop needs a reason to be shown | `pf loop list --group <g>` prints it, so a switched-off monitor is visible. |
| An unknown loop or key is refused | A typo that silently does nothing is the failure the file exists to prevent. |

`pf loop list --group <g>` shows the effective loops with a `source` column
(registry or group) and a waiver count, then the disabled loops with their
reasons. `pf loop run <loop>` on a disabled loop says why and exits 1.

## What a loop knows

An LLM-backed loop's system prefix is, in order: `platform/toolkits/ROUTING.md`,
`loop-constraints.md`, the group `CLAUDE.md`, the project `CLAUDE.md`, and the
project's context card. The card renders the graph; the two `CLAUDE.md` files
carry what the graph cannot encode. A business rule written there is what
teaches the loop: "futures do not settle at weekends" is why a Monday freshness
breach on `futures_prices` is the calendar and not the feed. Findings, run ids
and timestamps go in the user turn, after the cache breakpoint, never in the
prefix.

## Anatomy of a run

```
schedule → constraints → state (STATE.md) → circuit breaker → body
        → gate.yaml → ledger (loop-ledger.json) → STATE.md → escalate or stop
```

## Failure modes catalogued

- **Agent skips the impact gate.** Observed in this repo: staging was regenerated,
  three marts broke, zero impact reports in the window. Fixed by moving the gate
  into `pf check`, the pre-commit hook and the PreToolUse hook.
- **Loop retries a broken fix forever.** Bounded by `escalate_after: 3`, counted
  in the ledger so a restart does not reset it.
- **A loop edits shared infra.** Blocked by `platform_denylist` in `gate.yaml`.
- **Sister contention on the tracking DB.** Bounded lock-retry in `pf.obs`.
