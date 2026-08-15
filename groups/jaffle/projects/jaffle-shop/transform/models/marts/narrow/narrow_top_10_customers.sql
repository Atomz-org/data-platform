select
    customer_id,
    customer_name,
    lifetime_spend
from {{ ref('dim_customer_360') }}
order by lifetime_spend desc
limit 10
