---
name: add-anomaly-tests
description: >
  Add Elementary anomaly monitors (volume, freshness, dimension, column,
  schema changes) to a model. Triggers when: a table needs monitoring no
  fixed-rule test can express, "watch this table", "alert if rows drop",
  detecting drift/late data/schema breaks, or after a test_too_strict verdict
  suggested a monitor instead of a threshold.
---
# Elementary anomaly monitors

A dbt test asserts a rule (`status in ('placed', 'shipped')`). An Elementary
monitor learns a baseline from history and flags departures (order volume
dropped to a third of its learned normal). **Add a monitor exactly where a
rule cannot be written down** — volumes, freshness, distributions. If the rule
can be stated, state it: that is a dbt or dbt-expectations test
(`dbt-testing: add-tests`), which fails deterministically and needs no
history.

The recording is already on: the `elementary` tool declares the package in
every project, and every `dbt build` feeds the `main_elementary` schema.
Declaring a monitor is a normal edit to the model's own yml.

## Reference use case

Elementary's own demo — `jaffle-shop-goes-online` (github.com/elementary-data/
jaffle-shop-goes-online-forked) — monitors an e-commerce jaffle shop, and this
platform's `jaffle/jaffle-shop` marts carry the same patterns applied to our
ontology. Read `groups/jaffle/projects/jaffle-shop/transform/models/marts/orders.yml`
for the worked example. The essentials:

```yaml
models:
  - name: orders
    config:
      elementary:
        timestamp_column: "ordered_at"     # REQUIRED for time-bucketed monitors
    data_tests:
      - elementary.volume_anomalies:
          config: {severity: warn}
      - elementary.dimension_anomalies:
          dimensions: [is_food_order, is_drink_order]
          config: {severity: warn}
    columns:
      - name: order_total
        data_tests:
          - elementary.column_anomalies:
              column_anomalies: [zero_count, zero_percent]
              config: {severity: warn}
```

## Which monitor, from which role

The ontology already says what a column means; monitors follow the role the
same way generated tests and recce checks do:

| Ontology role / shape | Monitor | Watches for |
|---|---|---|
| `event_time` on the grain | `config: elementary: timestamp_column` | (prerequisite, not a test — buckets every other monitor by time) |
| the table itself | `elementary.volume_anomalies` | rows per bucket collapsing or exploding |
| `event_time`, arrival matters | `elementary.freshness_anomalies` | data landing later than it has historically |
| `status_enum`, `geo_country`, boolean flags | `elementary.dimension_anomalies` + `dimensions:` | a category's share drifting (recce sees the *change between builds*; this sees drift over time) |
| `money_amount`, counts | `elementary.column_anomalies` + `[zero_count, zero_percent, missing_count]` | nulls/zeros creeping into a measure |
| contract-critical tables | `elementary.schema_changes` | columns added, removed, retyped |

## Procedure

1. **Confirm the recording exists.** `pf tool doctor <group> <project>` — the
   `elementary` row must be enabled; then check the tables are there:
   ```bash
   pf tool elementary run <group> <project>    # first time only: creates them
   ```
2. **Pick the timestamp column from the ontology**, not by guessing: the
   mart's `event_time` role (see `contracts/annotations.yaml`). A monitor
   without a `timestamp_column` compares whole-table snapshots — legal, far
   weaker.
3. **Declare the monitor in the model's own yml** (the project owns it — this
   is a judgement about one table, which is why no generator writes it).
4. **Build twice before trusting it.** Anomaly detection needs history; on the
   first build every monitor passes vacuously. `pf seed` twice, or wait for
   the schedule, then read the result (`triage-observability`).

## Rules

- **Anomaly monitors are `severity: warn`.** An anomaly is a question, not a
  verdict — a Black Friday volume spike is not a broken pipeline. Reserve
  `error` for the deterministic tests beside it.
- **Never monitor a PII column's values.** `column_anomalies` on counts
  (`missing_count`, `zero_count`) is fine; value-level metrics on a
  `pii_*`-role column put real values into `main_elementary`, which is
  durable and shared — the same argument that keeps PII out of recce checks.
- **Do not stack a monitor on what a rule already covers.** `accepted_values`
  plus `dimension_anomalies` on the same column answers the same question
  twice with two verdicts; use the rule for membership, the monitor for share.
- **The elementary schema is not yours.** Never `ref()` or edit
  `main_elementary` tables from project models; read them in triage instead.
- Results land in the same history as every other test — dbt's,
  dbt-expectations', the generated floor — and in the `edr` report.
