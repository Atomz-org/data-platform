---
name: triage-alerts
description: Read an Elementary test result or alert and decide what it means.
---
# Triage an anomaly

An anomaly is a **question about data**, not a defect report. Classify it before
touching anything — the same four classes `dbt-govern` uses for run failures:

| Class | What it looks like | What to do |
|---|---|---|
| `upstream_data` | Source volume moved; the mart followed | Fix or confirm at the source; the mart is behaving |
| `model_logic` | Parent normal, child anomalous | A join or filter changed the grain — this is a real bug |
| `stale_source` | Freshness anomaly, volume flat | Re-run after the load; nothing to change |
| `expected_change` | Anomaly coincides with a launch, migration or seasonality | Record it, then widen the window or add a `dimension` |

**Only `expected_change` justifies editing the test.** Loosening a threshold to
silence an alert you have not explained is how the platform learns to under-report
exactly the thing it was installed to catch. If you widen one, say why in the
test's `meta` so the next person reads the reason rather than re-deriving it.

## Reading the result

```bash
dbt test --select elementary                # run the tests
edr report                                  # the HTML report, if edr is installed
```

Test results live in Elementary's schema. The row that matters carries the
metric, the expected range and the actual value — quote all three when you report
an anomaly, because "volume anomaly on fct_orders" is not actionable and
"14,203 rows against an expected 38–42k" is.

## Then use the graph

`impact_analysis` on the anomalous model tells you who consumes it — that is who
is about to see the number, and whether this is worth waking someone for. Check
whether the parents are anomalous too before concluding the model is at fault;
an anomaly that runs all the way up the lineage is one incident, not six.

## What this does not do

It does not gate a merge, and it does not overrule a metric definition. If an
anomaly makes you want to change what a number *means*, that is a
`dbt-semantic` change and goes through the semantic layer, not through a test.
