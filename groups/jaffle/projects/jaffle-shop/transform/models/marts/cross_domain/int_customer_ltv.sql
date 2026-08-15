with 
c as (
    select * from {{ ref('stg_customers') }}
),

o as (
    select * from {{ ref('stg_orders') }}
),

oi as (
    select * from {{ ref('order_items') }}
),

customer_orders as (
    select
        c.customer_id,
        count(distinct o.order_id) as total_orders,
        min(o.ordered_at) as first_order_at,
        max(o.ordered_at) as last_order_at
    from c
    left join o
        on c.customer_id = o.customer_id
    group by c.customer_id
),

customer_spend as (
    select
        o.customer_id,
        sum(oi.supply_cost) as total_spend,
        avg(oi.supply_cost) as avg_item_cost,
        count(distinct oi.product_id) as distinct_products_purchased
    from o
    inner join oi
        on o.order_id = oi.order_id
    group by o.customer_id
)

select
    co.customer_id,
    coalesce(cs.total_spend, 0) as lifetime_spend,
    co.total_orders,
    case
        when co.total_orders > 0
            then coalesce(cs.total_spend, 0) / co.total_orders
        else 0
    end as avg_order_value,
    cs.distinct_products_purchased,
    co.first_order_at,
    co.last_order_at,
    {{ dbt.datediff("co.first_order_at", "co.last_order_at", "day") }} as customer_tenure_days,
    case
        when co.total_orders >= 10 and coalesce(cs.total_spend, 0) >= 500 then 'platinum'
        when co.total_orders >= 5 and coalesce(cs.total_spend, 0) >= 200 then 'gold'
        when co.total_orders >= 2 then 'silver'
        else 'bronze'
    end as ltv_tier
from customer_orders as co
left join customer_spend as cs
    on co.customer_id = cs.customer_id
