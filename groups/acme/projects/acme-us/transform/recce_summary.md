# Recce Summary
## Manifest Information
|        |Manifest            |Catalog             |
|--------|--------------------|--------------------|
|Base    |2026-08-13 14:34:08 |2026-08-13 14:34:08 |
|Current |2026-08-13 14:39:08 |2026-08-13 14:34:08 |

## Lineage Graph

```mermaid
graph LR
model.acme_us.fct_payments["fct_payments

[What's Changed]
Code, Value Diff"]
style model.acme_us.fct_payments stroke:#ffa502
model.acme_us.fct_payments---->model.acme_us.fct_revenue
model.acme_us.fct_payments---->semantic_model.acme_us.payments
model.acme_us.fct_revenue["fct_revenue"]
model.acme_us.fct_revenue---->exposure.acme_us.exec_weekly_dashboard
semantic_model.acme_us.payments["payments"]
semantic_model.acme_us.payments---->metric.acme_us.revenue
semantic_model.acme_us.payments---->metric.acme_us.gross_payment_volume
semantic_model.acme_us.payments---->metric.acme_us.payment_count
exposure.acme_us.exec_weekly_dashboard["exec_weekly_dashboard"]
metric.acme_us.revenue["revenue"]
metric.acme_us.revenue---->metric.acme_us.aov
metric.acme_us.revenue---->metric.acme_us.revenue_mom_growth
metric.acme_us.gross_payment_volume["gross_payment_volume"]
metric.acme_us.payment_count["payment_count"]
metric.acme_us.payment_count---->metric.acme_us.aov
metric.acme_us.aov["aov"]
metric.acme_us.revenue_mom_growth["revenue_mom_growth"]

```

## Checks Summary
|Checks Run|Data Mismatch Detected|
|----------|----------------------|
|    17    |           3          |


### Checks of Data Mismatch Detected
|Name                                    |Type       |Mismatched Nodes|
|----------------------------------------|-----------|----------------|
|Value diff — fct_payments               |Value Diff |fct_payments    |
|Category drift — fct_payments.plan_tier |Query Diff |N/A             |
|Category drift — fct_revenue.plan_tier  |Query Diff |N/A             |
