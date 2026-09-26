# Concepts

What each model is an instance of, and how a row is identified.

| model | concept | identity | meaning |
|---|---|---|---|
| `customers` | Customer | customer_id | A party that buys. May be a person or an organization. |
| `dim_customer_360` | Customer | customer_id | A party that buys. May be a person or an organization. |
| `exec_company_kpis_monthly` | — | — |  |
| `locations` | Location | location_id | A geography. Country, region, or address. |
| `met_weekly_revenue_by_store` | Location | location_id | A geography. Country, region, or address. |
| `ml_feature_customer_churn` | Customer | customer_id | A party that buys. May be a person or an organization. |
| `order_items` | — | order_item_id |  |
| `orders` | Order | order_id | A one-off purchase commitment. |
| `products` | Product | product_id | A sellable thing. Plans and SKUs are Products. |
| `rev_etl_crm_customer_sync` | Customer | customer_id | A party that buys. May be a person or an organization. |
| `rev_etl_email_segment_at_risk` | Customer | customer_id | A party that buys. May be a person or an organization. |
| `rev_etl_email_segment_high_value` | Customer | customer_id | A party that buys. May be a person or an organization. |
| `rev_etl_inventory_reorder` | Location | location_id | A geography. Country, region, or address. |
| `rpt_campaign_effectiveness` | — | campaign_id |  |
| `rpt_customer_acquisition_funnel` | — | — |  |
| `rpt_customer_segments` | — | — |  |
| `rpt_loyalty_program_health` | — | — |  |
| `rpt_stock_alerts` | Product | product_id | A sellable thing. Plans and SKUs are Products. |
| `rpt_store_pnl` | Location | location_id | A geography. Country, region, or address. |
| `scr_customer_churn_propensity` | Customer | customer_id | A party that buys. May be a person or an organization. |
| `supplies` | — | supply_id |  |
| `view_store_mgr_daily_report` | Location | location_id | A geography. Country, region, or address. |
| `view_store_mgr_inventory_status` | Location | location_id | A geography. Country, region, or address. |
| `view_store_mgr_product_performance` | — | store_id |  |
| `view_store_mgr_staff_schedule` | — | shift_id |  |

## Column roles

Every column carries `pf.role` in the manifest. What a role means for a query:

| role | rule |
|---|---|
| `event_time` | the time axis; the default for any trend or period |
| `foreign_key` | a join to another model along a declared relationship |
