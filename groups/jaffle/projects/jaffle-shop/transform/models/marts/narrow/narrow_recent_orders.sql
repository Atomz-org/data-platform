select
    order_id,
    customer_id,
    ordered_at
from {{ ref('stg_orders') }}
order by ordered_at desc
limit 100
