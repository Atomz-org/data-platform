---
name: build-semantic-layer
description: Create MetricFlow semantic models, dimensions and metrics.
---
# Semantic layer (MetricFlow on dbt Core)

The mart declares the grain; the semantic layer declares how to aggregate it.

```yaml
semantic_models:
  - name: payments
    model: ref('fct_payments')
    defaults: {agg_time_dimension: paid_at}
    entities:
      - {name: payment_id, type: primary}
      - {name: customer, type: foreign, expr: customer_id}
    dimensions:
      - {name: paid_at, type: time, type_params: {time_granularity: day}}
      - {name: status, type: categorical}
    measures:
      - {name: payment_amount, agg: sum, expr: amount_usd}
      - {name: payments, agg: count, expr: payment_id}

metrics:
  - name: revenue
    label: Revenue
    type: simple
    type_params: {measure: payment_amount}
    filter: "{{ Dimension('payment__status') }} = 'succeeded'"
```

Derive the `agg_time_dimension` from the column annotated `event_time`, and the
measures from `money_amount` / `quantity`. Ratio and derived metrics compose
existing metrics — never recompute a numerator in SQL.

Add `saved_queries` with `exports` for anything a dashboard reads, so the BI table
still derives from the single definition.
