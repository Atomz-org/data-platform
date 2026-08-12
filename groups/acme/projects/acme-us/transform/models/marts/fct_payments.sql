-- Grain: one row per payment attempt. (edited)
-- Note this mart has no `revenue` column: which statuses count is a policy,
-- and policy lives in the semantic layer so it is defined exactly once.
select
    p.payment_id,
    p.customer_id,
    p.subscription_id,
    p.amount,
    p.currency_code,
    p.payment_status,
    p.paid_at,
    c.customer_segment,
    c.country_code,
    s.plan_tier
from {{ ref('stg_stripe__charges') }} p
left join {{ ref('stg_stripe__customers') }}     c using (customer_id)
left join {{ ref('stg_stripe__subscriptions') }} s using (subscription_id)
