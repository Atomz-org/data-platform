---
name: add-anomaly-tests
description: Add Elementary anomaly-detection tests to a model or source.
---
# Anomaly tests

Elementary tests assert against a model's **own history**, not against a value
you pick. That is the whole reason to reach for one: nobody knows what next
week's row count should be, and everybody knows it should not halve overnight.

Install first — these are package tests, not built-ins:

```yaml
# transform/packages.yml
- package: elementary-data/elementary
  version: [">=0.16.0", "<0.20.0"]
```

Elementary also needs an `on-run-end` hook and its own schema. Add both
deliberately; they change what every run writes.

## Which test, by what you are protecting

| Worry | Test |
|---|---|
| Loads stopped, or doubled | `volume_anomalies` |
| Source went stale | `freshness_anomalies` on the source, not the mart |
| A column drifted — nulls, cardinality, average | `column_anomalies` |
| A category appeared or vanished | `dimension_anomalies` with `dimensions:` |
| A join started dropping rows | `volume_anomalies` on the mart *and* its parent |

## The rules that matter here

**Anomaly tests are `warn`, built-in tests are `error`.** A key that is not
unique is a broken model; a row count 3σ low is a question. Severity is how the
two stay distinguishable, and a run where everything is `error` gets ignored
wholesale the first busy week.

**Put freshness on the source.** A mart is stale because its source was, and the
mart test names the wrong thing to go fix.

**Set `time_bucket` to the model's grain.** `meta.grain` already declares it —
a daily mart bucketed hourly reports an anomaly every night at 00:00.

**Give it history before you trust it.** Elementary needs enough runs to have a
baseline; a test added today and alerting tomorrow is comparing against almost
nothing. `training_period` and `detection_period` control that window.

**Never let an anomaly test gate a merge.** It reports on data, and the merge
gate judges code. `pf impact` is the merge question; this is the morning
question.

## Before adding one

Run `impact_analysis` on the model. A test on a hub model that forty things
depend on is worth more than one on a leaf, and the graph is what tells you
which you are looking at.
