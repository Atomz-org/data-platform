-- Every customer should have at least one order
select customer_id
from {{ ref('customers') }}
where count_lifetime_orders is null or count_lifetime_orders <= 0
