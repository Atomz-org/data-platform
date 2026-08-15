-- Analysis: Distribution of customer lifetime value
-- This analysis is used for ad-hoc reporting, not materialized

select
    case
        when lifetime_spend < 50 then 'Under $50'
        when lifetime_spend < 200 then '$50-200'
        when lifetime_spend < 500 then '$200-500'
        else 'Over $500'
    end as ltv_bucket,
    count(*) as customer_count,
    round(avg(lifetime_spend), 2) as avg_spend,
    round(avg(count_lifetime_orders), 1) as avg_orders
from {{ ref('customers') }}
group by 1
order by min(lifetime_spend)
