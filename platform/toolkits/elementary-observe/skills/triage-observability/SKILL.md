---
name: triage-observability
description: >
  Read and triage what Elementary recorded: failing or anomalous tests, run
  history, schema changes, the edr report. Triggers when: a test or monitor
  fired, "why did the build fail", "is the data healthy", investigating slow
  models or flaky tests, or before trusting a mart for a report.
---
# Triaging with Elementary

Every dbt build records itself into `main_elementary` — run results, test
results (all frameworks: dbt's own, dbt-expectations, the generated floor,
anomaly monitors), timings and schema snapshots. Triage means querying that
history, not re-reading the log of whichever run happened to fail. One
failure is an incident; the history says whether it is new, recurring, or
flaky — and those get different fixes.

## Where to look

```bash
pf tool elementary report <group> <project>   # render the HTML report (needs edr)
pf tool elementary serve <group> <project>    # read it at :8020
```

No `edr` on this machine? The tables answer everything the report does.
Query the project's DuckDB (schema `main_elementary`), read-only:

| question | table |
|---|---|
| what failed, when, how often | `elementary_test_results` |
| every run of every node, with timing | `dbt_run_results` |
| what a monitor actually measured | `data_monitoring_metrics` |
| anomaly verdicts per bucket | `anomaly_threshold_sensitivity` / test results detail |
| schema now vs before | `dbt_columns` + `schema_columns_snapshot` |

Start with recurrence, always:

```sql
select test_unique_id, status, count(*) as runs,
       max(detected_at) as last_seen
from main_elementary.elementary_test_results
group by 1, 2 order by last_seen desc;
```

## Classify before fixing

Same discipline as `dbt-govern: troubleshoot-runs`, extended one row for
monitors:

| verdict | evidence in the history | fix |
|---|---|---|
| `upstream_data` | test green for weeks, failed when a source's volume/freshness also moved | fix the source; the model is innocent |
| `model_logic` | first failure coincides with a change to the model (`dbt_run_results` shows the deploy) | fix the model |
| `stale_source` | freshness monitor fired, volume normal | re-run after the source lands |
| `test_too_strict` | fails intermittently with values that are business-plausible | loosen the rule — or replace it with a monitor (`add-anomaly-tests`) |
| `expected_anomaly` | monitor fired on a known event (launch, campaign, backfill) | acknowledge; do not delete the monitor for being right |

**An anomaly you cannot classify is a finding.** Report it as unexplained
rather than assuming `expected_anomaly` — the monitor's whole value is that
nobody was asking the question.

## The composed picture

Three tools answer three different questions about the same change; a triage
that stops at one is incomplete:

| question | tool |
|---|---|
| what *could* this break | `impact_analysis` (knowledge graph) |
| what *did* the change move | `recce-review` (diff against baseline) |
| what has been true *over time* | this — Elementary's history |

In Dagster the `elementary_report` asset (group `observability`) refreshes the
report downstream of the marts and carries the deep link on every run.

## Rules

- **Never edit `main_elementary` tables or `transform/edr_target/`.** The
  record of what happened is gate-denied for the same reason `provenance/**`
  is: you may not edit the record of what you did. The report is regenerated,
  never patched.
- **Connect read-only** when querying the warehouse — a sister project or a
  running build may hold the write lock.
- A monitor that fires every week and is acknowledged every week is a broken
  monitor or an unowned problem. Either tune it (`add-anomaly-tests` rules)
  or file the finding with the model's owner; do not let it become wallpaper.
- Timings live in `dbt_run_results` — a model whose runtime doubled is a
  finding even when every test is green.
