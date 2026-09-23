---
type: Table
title: dim_customer_360
description: 'marts at grain: undeclared'
okf_x_source_of_truth: true
okf_x_table_confidence: 0.0
okf_x_concept: Customer
okf_x_layer: marts
okf_x_grain: null
okf_x_columns_withheld: 0
okf_x_kg_node: model:dim_customer_360
---

# Schema

| Column | Type | Role | Description | Confidence |
|---|---|---|---|---|
| `acquisition_source` | VARCHAR |  | — | 0.00 |
| `avg_order_value` | DOUBLE |  | — | 0.00 |
| `campaign_response_rate_pct` | VARCHAR |  | — | 0.00 |
| `campaigns_responded_to` | BIGINT |  | — | 0.00 |
| `customer_id` | VARCHAR | foreign_key | Reference to another concept instance. (primary key) | 1.00 |
| `customer_name` | VARCHAR |  | — | 0.00 |
| `customer_tenure_days` | BIGINT |  | — | 0.00 |
| `days_since_last_order` | BIGINT |  | — | 0.00 |
| `distinct_stores_visited` | BIGINT |  | — | 0.00 |
| `first_order_at` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `frequency_score` | BIGINT |  | — | 0.00 |
| `last_order_at` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `lifetime_spend` | DECIMAL |  | — | 0.00 |
| `loyalty_enrolled_at` | TIMESTAMP | event_time | When the event occurred. Candidate agg time dimension. | 1.00 |
| `loyalty_lifecycle_stage` | VARCHAR |  | — | 0.00 |
| `loyalty_member_id` | VARCHAR | foreign_key | Reference to another concept instance. | 1.00 |
| `loyalty_points_balance` | VARCHAR |  | — | 0.00 |
| `loyalty_tenure_days` | BIGINT |  | — | 0.00 |
| `loyalty_tier` | VARCHAR |  | — | 0.00 |
| `ltv_tier` | VARCHAR |  | — | 0.00 |
| `marketing_engagement_level` | VARCHAR |  | — | 0.00 |
| `monetary_score` | BIGINT |  | — | 0.00 |
| `preferred_store_id` | VARCHAR | foreign_key | Reference to another concept instance. | 1.00 |
| `preferred_store_name` | VARCHAR |  | — | 0.00 |
| `preferred_store_visit_pct` | VARCHAR |  | — | 0.00 |
| `preferred_store_visits` | BIGINT |  | — | 0.00 |
| `recency_score` | BIGINT |  | — | 0.00 |
| `rfm_segment_code` | VARCHAR |  | — | 0.00 |
| `rfm_total_score` | BIGINT |  | — | 0.00 |
| `top1_product_id` | VARCHAR | foreign_key | Reference to another concept instance. | 1.00 |
| `top1_product_name` | VARCHAR |  | — | 0.00 |
| `top1_product_share_pct` | VARCHAR |  | — | 0.00 |
| `top1_purchase_count` | BIGINT |  | — | 0.00 |
| `top2_product_id` | VARCHAR | foreign_key | Reference to another concept instance. | 1.00 |
| `top2_product_name` | VARCHAR |  | — | 0.00 |
| `top3_product_id` | VARCHAR | foreign_key | Reference to another concept instance. | 1.00 |
| `top3_product_name` | VARCHAR |  | — | 0.00 |
| `total_coupons_redeemed` | BIGINT |  | — | 0.00 |
| `total_discount_received` | DECIMAL |  | — | 0.00 |
| `total_items_purchased` | VARCHAR |  | — | 0.00 |
| `total_orders` | BIGINT |  | — | 0.00 |

# Concept

Instantiates [Customer](/concepts/Customer.md).

# Lineage

* **Upstream:** [customers](/tables/customers.md), `int_customer_loyalty_enriched`, `int_customer_ltv`, `int_customer_marketing_response`, `int_customer_preferred_products`, `int_customer_preferred_store`, `int_customer_rfm_scores`
* **Downstream:** `cmp_loyalty_vs_non_loyalty`, `dist_customer_order_frequency`, `kpi_avg_customer_lifetime`, `mkt_customer_lifecycle_stage`, `mkt_customer_win_back`, `mkt_retention_driver_analysis`, `ml_feature_basket_size`, [ml_feature_customer_churn](/tables/ml_feature_customer_churn.md), `narrow_top_10_customers`, `rank_customers_by_basket_size`, `rank_customers_by_frequency`, `rank_customers_by_ltv`, `rank_customers_by_recency`, [rev_etl_crm_customer_sync](/tables/rev_etl_crm_customer_sync.md), [rev_etl_email_segment_at_risk](/tables/rev_etl_email_segment_at_risk.md), [rev_etl_email_segment_high_value](/tables/rev_etl_email_segment_high_value.md), `rev_etl_email_segment_new`, `rpt_360_customer_health_dashboard`, `rpt_churn_risk_dashboard`, `rpt_customer_journey_summary`, `rpt_high_value_customer_profile`, [scr_customer_churn_propensity](/tables/scr_customer_churn_propensity.md), `view_store_mgr_customer_insights`, `wide_coupon_redemption_detail`, `wide_customer_summary`, `wide_loyalty_member_summary`, `wide_order_with_customer`
* **Read by:** `marketing_analytics` (Marketing Team)

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
