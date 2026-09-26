# Metrics

## Cube `acme_eu_core` on `fct_payments`

Ask it with `wren cube query --cube <name> --measures <m> --dimensions <d>`; the
engine writes the GROUP BY.

Measures:

| measure | expression | meaning |
|---|---|---|
| `active_customers` | `sum(case when is_active then 1 else 0 end)` | Active Customers |
| `aov` | `sum(amount) / nullif(count(payment_id), 0)` | Average Order Value |
| `gross_payment_volume` | `sum(amount)` | Gross Payment Volume |
| `payment_count` | `count(payment_id)` | Payments |
| `revenue` | `sum(amount)` | Revenue |

Dimensions: `country_code`, `customer_segment`, `payment_status`, `plan_tier`
Time dimensions: `created_at`, `paid_at`

## Metric definitions

The governed definitions, as the semantic layer declares them.

| metric | type | model | how | unit | filter | meaning |
|---|---|---|---|---|---|---|
| `active_customers` | simple | `dim_customers` | `sum(case when is_active then 1 else 0 end)` |  |  | Customers with at least one active subscription. |
| `aov` | ratio | `fct_payments` | `revenue / payment_count` |  |  | Revenue divided by succeeded payment count. |
| `gross_payment_volume` | simple | `fct_payments` | `sum(amount)` |  |  | All payment attempts regardless of outcome. |
| `payment_count` | simple | `fct_payments` | `count(payment_id)` |  | payment_status = 'succeeded' | Count of succeeded payments. |
| `revenue` | simple | `fct_payments` | `sum(amount)` |  | payment_status = 'succeeded' | Net revenue — succeeded payments only. The single definition. |
| `revenue_mom_growth` | derived | `fct_payments` | `derived` |  |  | Month-over-month change in net revenue. |
