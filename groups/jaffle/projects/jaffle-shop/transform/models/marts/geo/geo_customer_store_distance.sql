with

orders as (

    select * from {{ ref('stg_orders') }}

),

customers as (

    select * from {{ ref('stg_customers') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

customer_store_orders as (

    select
        o.customer_id,
        o.location_id,
        count(*) as order_count,
        sum(o.order_total) as total_spend,
        min(o.ordered_at) as first_order_at,
        max(o.ordered_at) as last_order_at

    from orders o
    where o.customer_id is not null
    group by o.customer_id, o.location_id

),

ranked as (

    select
        *,
        row_number() over (
            partition by customer_id order by order_count desc, total_spend desc
        ) as store_rank

    from customer_store_orders

),

customer_total as (

    select
        customer_id,
        sum(order_count) as total_orders_all_stores,
        count(distinct location_id) as stores_visited

    from customer_store_orders
    group by customer_id

)

select
    r.customer_id,
    c.customer_name as customer_name,
    r.location_id as store_id,
    l.location_name as store_name,
    r.store_rank,
    case
        when r.store_rank = 1 then 'primary'
        when r.store_rank = 2 then 'secondary'
        else 'tertiary'
    end as store_affinity,
    r.order_count,
    r.total_spend,
    r.first_order_at,
    r.last_order_at,
    ct.total_orders_all_stores,
    ct.stores_visited,
    round(r.order_count * 100.0 / nullif(ct.total_orders_all_stores, 0), 2) as pct_orders_at_store

from ranked r
left join customers c on r.customer_id = c.customer_id
left join locations l on r.location_id = l.location_id
left join customer_total ct on r.customer_id = ct.customer_id
where r.store_rank <= 3
