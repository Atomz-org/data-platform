# Elementary — data observability for globex/globex-core

Every `dbt build` here records itself: the `elementary-data/elementary`
package hooks on-run-start/on-run-end and writes run results, test results
(dbt's own, dbt-expectations', everyone's), model timings and schema snapshots
into the `main_elementary` schema beside the marts. Observability is queryable
tables with history, not a log that scrolled away.

## The loop

```bash
pf seed globex globex-core                     # every build records itself
pf tool elementary run globex globex-core      # first time: create the tables
pf tool elementary report globex globex-core   # render the HTML report
pf tool elementary serve globex globex-core    # read it in a browser
```

`report` and `serve` need the CLI, installed isolated (it cannot share a
lockfile with recce): `uv tool install 'elementary-data[duckdb]==0.25.*'`.
Recording needs nothing — the package rides inside dbt.

## What is declared where

| file | declaration | owner |
|---|---|---|
| `transform/packages.yml` | the package, minor-pinned | `pf bootstrap` adds, your pin wins |
| `transform/dbt_project.yml` | `models: elementary: +schema` | inserted once, then yours |
| `transform/profiles.yml` | the `elementary` profile `edr` connects with | re-added by bootstrap if dropped |

`transform/edr_target/` is a build artefact (the rendered report) and is
gate-denied like `target/` — regenerate it, never edit it.

## Anomaly detection

The package also ships anomaly tests (`elementary.volume_anomalies`,
`elementary.freshness_anomalies`, ...). They are deliberately not generated:
an anomaly threshold is a judgement about one table's behaviour, so declare
them in the model's own yml where that judgement lives. The
`elementary-observe` skills are the how — `add-anomaly-tests` to declare a
monitor (with `jaffle/jaffle-shop`'s marts as the worked example, after
Elementary's own jaffle-shop-goes-online demo), `triage-observability` to
read what fired. Results land in the same tables and the same report.

## In Dagster

The `elementary_report` asset runs downstream of this project's marts and
attaches the report link. The recording itself has no asset — it happens
inside every dbt build already.
