# Stage 5 — MetricFlow

**Goal condition:** the business quantities have one definition each, and it runs.

A mart nothing measures is a table. The point of the semantic layer is that
"revenue" has exactly one definition in this company — the alternative is two
dashboards filtering differently and nobody able to say which is right.

## Evaluate

```bash
pf align evaluate <group> <project> --stage metrics
```

- **`no-semantic-models` / `no-metrics`** — every question falls back to ad-hoc
  SQL.
- **`mart-uncovered`** — a mart with no semantic model. Full coverage is rarely
  the goal; most marts are intermediate. Cover what people ask about and say in
  `decisions/` why the rest are not.
- **`metric-undescribed`** — the description is the definition an agent quotes
  when it answers. Without one the metric is a name and a sum.
- **`no-time-spine`** — cumulative, derived and offset metrics all need it, and
  they fail at query time rather than at parse.

## Implement

Two files under `transform/models/semantic/`.

**Semantic model** — binds a mart to entities, dimensions and measures. The
annotations from the ontology stage tell you which column is which: `natural_key`
becomes the primary entity, a column with `links` becomes a foreign entity,
`event_time` becomes the `agg_time_dimension`, `money_amount` becomes a measure.

```yaml
semantic_models:
  - name: orders
    model: ref('fct_orders')
    defaults: {agg_time_dimension: ordered_at}
    entities:
      - {name: order, type: primary, expr: order_id}
      - {name: customer, type: foreign, expr: customer_id}
    dimensions:
      - name: ordered_at
        type: time
        type_params: {time_granularity: day}
      - {name: order_status, type: categorical}
    measures:
      - {name: order_total, agg: sum, expr: amount, agg_time_dimension: ordered_at}
```

**Metrics** — the aggregation policy. The mart declares the grain; the metric
declares what is done with it.

```yaml
metrics:
  - name: revenue
    label: Revenue
    description: Net revenue — completed orders only. The single definition.
    type: simple
    type_params: {measure: order_total}
    filter: "{{ Dimension('order__order_status') }} = 'completed'"
```

Prefer **composing** over recomputing. An average order value is a `ratio` of two
existing metrics, not a new `sum(x)/count(y)`; a growth rate is `derived` with an
`offset_window`. Recomputing is how the second definition gets in.

### Where the definitions come from

Not from you. The source repository already computed these figures somewhere —
in a mart called `*_kpis` or `*_metrics`, in an Evidence page, in a `analyses/`
query. Port those definitions and cite where each came from in the description.
Inventing a revenue definition for a company you onboarded this morning is
exactly the guess this platform tells you to escalate.

## Validate

```bash
pf align validate <group> <project> --stage metrics
```

Conditions: semantic models declared, metrics declared, the semantic manifest
accepted by dbt, and a metric actually answering a query.

The last one reports **unexercised** if the MetricFlow CLI is not installed
(`uv add dbt-metricflow`). Parsing proves the definitions are well-formed, not
that they run. Do not report an unexercised check as a pass — say which of the
two you have.

```bash
mf query --metrics revenue --group-by metric_time__month --limit 5
```

## Then

The review stage. A metric that parses and returns a number is still not known to
be *right*; the diff against the previous state is what says whether it changed
anything it should not have.
