---
name: evidence-number-formats
description: 'Evidence formats: declared per metric (meta.unit/format), audited (fmt-*), tiles sized by magnitude, stocks read at latest day'
type: project
status: active
agent: claude-code
---

stack: [pf.projections.evidence, pf.projections.report_audit, Evidence 40, ssf]

- Metric formats are declared on the MetricFlow metric (`config.meta.unit: INR|pct|lots`
  or `meta.format`), resolved once by `metric_format`, stamped into each compiled query
  as `-- format: <code>`; `pf report audit` rules fmt-unit / fmt-missing / fmt-unscaled
  check every component that renders a metric against it.
- Evidence's bare currency code (`inr`, `usd`) does NOT auto-scale inside <BigValue>:
  tiles need an explicit Excel scale. `kpi_format(fmt, magnitude)` sizes it from the
  value measured at build (`_kpi_magnitudes`): `"₹"#,##0.00,,,,"T"` → ₹485.09T.
- A measure with `non_additive_dimension` on its time dimension compiles as rollup
  `stock`: summed across dims within a day, read at the latest day on tiles and
  breakdowns (`_as_of_latest`). Open interest summed over days is meaningless.
- collect_metrics walks simple → ratio → derived: dbt's metric order is not ours, and
  a ratio listed before its components used to be skipped silently.
- Ratio numerators/denominators and labels "(component)" never become KPI tiles.
