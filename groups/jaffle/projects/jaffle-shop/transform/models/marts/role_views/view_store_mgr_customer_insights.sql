with

customer_360 as (

    select * from {{ ref('dim_customer_360') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

store_customers as (

    select
        o.location_id as store_id,
        o.customer_id,
        c.customer_name,
        c.lifetime_spend,
        c.total_orders,
        c.ltv_tier,
        count(*) as orders_at_store

    from orders o
    inner join customer_360 c on o.customer_id = c.customer_id
    where o.customer_id is not null
    group by o.location_id, o.customer_id, c.customer_name, c.lifetime_spend, c.total_orders, c.ltv_tier

)

select
    store_id,
    ltv_tier,
    count(distinct customer_id) as customer_count,
    round(avg(lifetime_spend), 2) as avg_ltv,
    round(avg(orders_at_store), 2) as avg_orders_at_store,
    sum(orders_at_store) as total_orders_at_store

from store_customers
group by store_id, ltv_tier
