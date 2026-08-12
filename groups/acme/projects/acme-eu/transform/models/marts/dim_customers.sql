-- Grain: one row per customer.
with c as (select * from {{ ref('stg_stripe__customers') }}),
     s as (
        select customer_id,
               count(*)                                          as subscription_count,
               sum(case when subscription_status = 'active' then 1 else 0 end) as active_subscriptions,
               min(started_at)                                   as first_subscribed_at
        from {{ ref('stg_stripe__subscriptions') }}
        group by 1
     )
select
    c.customer_id,
    c.organization_id,
    c.customer_segment,
    c.country_code,
    c.created_at,
    coalesce(s.subscription_count, 0)   as subscription_count,
    coalesce(s.active_subscriptions, 0) as active_subscriptions,
    s.first_subscribed_at,
    coalesce(s.active_subscriptions, 0) > 0 as is_active
from c left join s using (customer_id)
