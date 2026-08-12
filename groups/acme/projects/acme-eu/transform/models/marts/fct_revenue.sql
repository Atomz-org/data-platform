-- Grain: one row per day per segment. The shape sisters union in _rollup —
-- identical because both derive from the same group ontology.
select
    cast(paid_at as date)               as revenue_date,
    customer_segment,
    plan_tier,
    currency_code,
    sum(amount)                         as gross_amount,
    sum(case when payment_status = 'succeeded' then amount else 0 end) as net_amount,
    count(*)                            as payment_count
from {{ ref('fct_payments') }}
group by all
