---
name: build-dashboard
description: Build or edit an Evidence page, chart, KPI or filter. Use for any dashboard, report or metric-visualisation request.
---
# Building a dashboard

## Procedure — in order

1. **Start from the metric, never the chart.** `pf report build` compiles every
   MetricFlow metric to `queries/metrics/<name>.sql`. Check what exists first:
   `ls reporting/queries/metrics/`. Missing number → add the metric in
   `transform/models/semantic/`, `pf seed`, then `pf report build`.
2. **Pick the form by the data's job**, not by habit:

   | Job | Component |
   |---|---|
   | one headline number | `<BigValue>` |
   | change over time | `<LineChart>` |
   | magnitude comparison across categories | `<BarChart swapXY=true>` |
   | composition of a whole | stacked `<BarChart>` — never a pie past 3 slices |
   | correlation | `<ScatterPlot>` |
   | lookup / detail | `<DataTable>` |

   Sometimes the honest answer is a number and a sentence, not a chart.
3. **Compose to the standard anatomy** — title + context sentence, one filter
   row, KPI row, primary trend, breakdowns, detail table with drill links.
4. **Colour by job, from the theme only.** Categorical hues in fixed order, never
   cycled; sequential is one hue light→dark; diverging is two hues around a
   neutral; status colours are reserved and ship with a label, never colour alone.
5. **Run `pf report audit`**, then `npm run build` — a broken query fails the
   build, which is the point of BI-as-code.

## Non-negotiables

- Never a dual-axis chart. Two measures of different scale → two charts, or index
  both to a common base.
- A legend is present for ≥2 series; ≤4 series are also direct-labelled.
- Never a number on every point. Label selectively.
- `avg()` of a ratio metric is a bug. Re-divide the carried components.
- Every page answers one question. If it answers three, it is three pages.

## References
Deep material lives in the vendored upstream, which this toolkit is adapted from:
`vendor/evidence-bi/.claude/skills/evidence-bi/references/` — `design-principles.md`,
`components.md`, `dbt-semantic-layer.md`, `enterprise-reporting.md`.
