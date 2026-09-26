# Scope — groups/jaffle/projects/jaffle-shop

This workspace is one project of the `jaffle` group. Every model in it is a
mart of `jaffle-shop` (MDL catalog `jaffle`, schema `jaffle_shop`),
addressed by its model name; the engine maps that name to the project's own warehouse.

- Answer only from the models, cubes and rules in this workspace. Another
  project's tables are not visible here and are never guessed at or joined.
- Columns that hold personal data are absent from this workspace by design.
  A question that needs one has no answer here, and saying so is the answer.
- Every query is planned through the MDL, dry-run, row-limited and recorded
  before it runs. Write one `SELECT` over model names exactly as listed.
- A governed number is its metric: answer it from the cube `jaffle_shop_core` or from `query_metrics`, never by recomputing it in SQL.
- A price is a unit price and a percentage is already a ratio: neither is
  summed or averaged across rows. Money is additive within one currency.

## Models

- `customers`
- `dim_customer_360`
- `exec_company_kpis_monthly`
- `locations`
- `met_weekly_revenue_by_store`
- `ml_feature_customer_churn`
- `order_items`
- `orders`
- `products`
- `rev_etl_crm_customer_sync`
- `rev_etl_email_segment_at_risk`
- `rev_etl_email_segment_high_value`
- `rev_etl_inventory_reorder`
- `rpt_campaign_effectiveness`
- `rpt_customer_acquisition_funnel`
- `rpt_customer_segments`
- `rpt_loyalty_program_health`
- `rpt_stock_alerts`
- `rpt_store_pnl`
- `scr_customer_churn_propensity`
- `supplies`
- `view_store_mgr_daily_report`
- `view_store_mgr_inventory_status`
- `view_store_mgr_product_performance`
- `view_store_mgr_staff_schedule`
