-- source extract for ml_feature_customer_churn (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    customer_id,
    days_since_last_order,
    lifetime_order_count,
    lifetime_spend,
    rfm_total_score,
    is_loyalty_member,
    order_trend_slope,
    churn_label_proxy
from main_marts.ml_feature_customer_churn
