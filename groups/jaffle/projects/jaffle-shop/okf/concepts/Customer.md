---
type: Concept
title: Customer
description: A party that buys. May be a person or an organization.
okf_x_defined_in: platform
okf_x_parent: Party
okf_x_identity: customer_id
okf_x_kg_node: concept:Customer
okf_x_platform_concept: ../../../../../../platform/okf/concepts/Customer.md
---

Defined by the platform ontology: [Customer](../../../../../../platform/okf/concepts/Customer.md).

# Instantiated by

* [adv_customer_health_matrix](/tables/adv_customer_health_matrix.md)
* [adv_customer_product_array](/tables/adv_customer_product_array.md)
* [adv_customers_never_used_coupon](/tables/adv_customers_never_used_coupon.md)
* [adv_first_purchase_product](/tables/adv_first_purchase_product.md)
* [adv_latest_event_per_customer](/tables/adv_latest_event_per_customer.md)
* [alert_coupon_abuse_flag](/tables/alert_coupon_abuse_flag.md)
* [coh_customer_monthly_cohort](/tables/coh_customer_monthly_cohort.md)
* [customers](/tables/customers.md)
* [dim_customer_360](/tables/dim_customer_360.md)
* [dq_duplicate_customers](/tables/dq_duplicate_customers.md)
* [fin_customer_profitability](/tables/fin_customer_profitability.md)
* [geo_cross_store_shopping](/tables/geo_cross_store_shopping.md)
* [geo_customer_store_distance](/tables/geo_customer_store_distance.md)
* [inc_met_daily_revenue](/tables/inc_met_daily_revenue.md)
* [int_customer_acquisition_source](/tables/int_customer_acquisition_source.md)
* [int_customer_channel_affinity](/tables/int_customer_channel_affinity.md)
* [int_customer_first_purchase_context](/tables/int_customer_first_purchase_context.md)
* [int_customer_loyalty_enriched](/tables/int_customer_loyalty_enriched.md)
* [int_customer_ltv](/tables/int_customer_ltv.md)
* [int_customer_marketing_response](/tables/int_customer_marketing_response.md)
* [int_customer_order_frequency_trend](/tables/int_customer_order_frequency_trend.md)
* [int_customer_preferred_products](/tables/int_customer_preferred_products.md)
* [int_customer_preferred_store](/tables/int_customer_preferred_store.md)
* [int_customer_product_preference](/tables/int_customer_product_preference.md)
* [int_customer_rfm_scores](/tables/int_customer_rfm_scores.md)
* [int_customer_status_monthly](/tables/int_customer_status_monthly.md)
* [int_revenue_per_customer_monthly](/tables/int_revenue_per_customer_monthly.md)
* [mega_wide_customer_master](/tables/mega_wide_customer_master.md)
* [mkt_campaign_fatigue](/tables/mkt_campaign_fatigue.md)
* [mkt_coupon_stacking_analysis](/tables/mkt_coupon_stacking_analysis.md)
* [mkt_customer_communication_preference](/tables/mkt_customer_communication_preference.md)
* [mkt_customer_journey_touchpoints](/tables/mkt_customer_journey_touchpoints.md)
* [mkt_customer_lifecycle_stage](/tables/mkt_customer_lifecycle_stage.md)
* [mkt_customer_next_best_action](/tables/mkt_customer_next_best_action.md)
* [mkt_customer_win_back](/tables/mkt_customer_win_back.md)
* [mkt_email_list_health](/tables/mkt_email_list_health.md)
* [mkt_loyalty_engagement_score](/tables/mkt_loyalty_engagement_score.md)
* [mkt_retention_driver_analysis](/tables/mkt_retention_driver_analysis.md)
* [ml_feature_customer_churn](/tables/ml_feature_customer_churn.md)
* [narrow_customer_ids](/tables/narrow_customer_ids.md)
* [narrow_top_10_customers](/tables/narrow_top_10_customers.md)
* [rank_customers_by_basket_size](/tables/rank_customers_by_basket_size.md)
* [rank_customers_by_frequency](/tables/rank_customers_by_frequency.md)
* [rank_customers_by_loyalty_points](/tables/rank_customers_by_loyalty_points.md)
* [rank_customers_by_ltv](/tables/rank_customers_by_ltv.md)
* [rank_customers_by_recency](/tables/rank_customers_by_recency.md)
* [rev_etl_crm_customer_sync](/tables/rev_etl_crm_customer_sync.md)
* [rev_etl_email_segment_at_risk](/tables/rev_etl_email_segment_at_risk.md)
* [rev_etl_email_segment_high_value](/tables/rev_etl_email_segment_high_value.md)
* [rev_etl_email_segment_new](/tables/rev_etl_email_segment_new.md)
* [rpt_churn_risk_dashboard](/tables/rpt_churn_risk_dashboard.md)
* [rpt_customer_journey_summary](/tables/rpt_customer_journey_summary.md)
* [rpt_customer_reactivation](/tables/rpt_customer_reactivation.md)
* [rpt_customer_satisfaction_composite](/tables/rpt_customer_satisfaction_composite.md)
* [rpt_high_value_customer_profile](/tables/rpt_high_value_customer_profile.md)
* [rpt_omnichannel_customer](/tables/rpt_omnichannel_customer.md)
* [rpt_revenue_concentration](/tables/rpt_revenue_concentration.md)
* [scr_customer_churn_propensity](/tables/scr_customer_churn_propensity.md)
* [wide_customer_summary](/tables/wide_customer_summary.md)

# Properties

| Property | Datatype | Role |
|---|---|---|
| `country` | string | geo_country |
| `created_at` | timestamp | event_time |
| `customer_id` | string | natural_key |
| `email` | string | pii_email |
| `id` | string | natural_key |
| `name` | string | pii_name |
| `segment` | string | status_enum |

# Relations

* Customer belongs to Organization — A customer may sit under a parent organization.
* Customer holds Subscription — The spine of any recurring-revenue model.
* Customer located in Location — 
* Customer participates in Interaction — 
* Customer pays Payment — 
* Customer places Order — 

# Raw tables that instantiate it

* `jaffle-seeds.raw_customers`

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
