select
    customer_type,
    count(*) as customer_count
from {{ ref('customers') }}
group by customer_type
