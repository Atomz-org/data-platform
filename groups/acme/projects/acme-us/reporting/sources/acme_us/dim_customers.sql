-- source extract for dim_customers (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    customer_id,
    customer_segment,
    country_code,
    created_at,
    subscription_count,
    active_subscriptions,
    organization_id,
    first_subscribed_at,
    is_active
from main_marts.dim_customers
