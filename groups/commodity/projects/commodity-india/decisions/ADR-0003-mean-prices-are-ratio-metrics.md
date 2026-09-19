# ADR-0003: Mean prices are ratio metrics, not `average` measures

**Status:** accepted · 2026-09-16

## Context

Every useful price metric here is a mean: average benchmark, average landed
price, average USD/INR. MetricFlow's `agg: average` computes that correctly for
MetricFlow queries, but pages roll daily rows up to their own display grain, and
an average cannot be re-aggregated; a sum and a count can.

When this was decided, the Evidence projection also wrote `agg: average` into
SQL verbatim as `average(x)`, which DuckDB does not have. That platform bug is
fixed (2026-09-16): the projection now emits `avg(x)` and carries an average's
sum and count itself. The ratio design stays, because it is explicit in the
semantic layer rather than reconstructed by one consumer of it.

## Decision

Every mean is a `ratio` metric over a `sum` component and a `count` component,
for example `avg_landed_price_inr = landed_price_inr_total / landed_price_days`.
Components are declared before the ratio that uses them, because the projection
resolves metrics in order. Components whose sums mean nothing on their own are
labelled "(component)".

`commodity_id` is the first categorical dimension on each fact's semantic model,
so generated queries group per commodity rather than across units.

## Consequences

- Seven component metrics appear in the card and get their own pages.
- `period_high_price_usd` and `period_low_price_usd` stay `max` / `min`, which
  re-aggregate correctly as they are.
- A future mean may use `agg: average` directly; the projection now handles it
  correctly. Existing means stay ratios so every consumer divides the same way.
- The two month-over-month metrics (`benchmark_price_mom_change`,
  `landed_price_mom_change`) use an `offset_window`. MetricFlow computes them;
  the Evidence projection cannot render an offset and skips them, so they have
  no report page.
- The generated overview (`reporting/pages/index.md`) sums the component
  metrics across every commodity for its headline KPIs. Those totals mix units
  and are not prices. Read prices on the per-metric pages, which group by
  commodity.
