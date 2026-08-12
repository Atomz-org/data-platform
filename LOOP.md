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
| `index-refresher` | on manifest change | L2 | 0 | yes | rebuild graph + context card |

Daily budget across all loops: **200,000 tokens**. The circuit breaker opens on
depletion, or after 3 consecutive failures of the same loop.

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
