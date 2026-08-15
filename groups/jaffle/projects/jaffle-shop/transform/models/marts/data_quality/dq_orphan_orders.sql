with

orders as (

    select * from {{ ref('stg_orders') }}

),

customers as (

    select * from {{ ref('stg_customers') }}

),

orphans as (

    select
        o.order_id,
        o.customer_id,
        o.location_id,
        o.ordered_at,
        o.order_total,
        o.subtotal

    from orders as o

    left join customers as c
        on o.customer_id = c.customer_id

    where c.customer_id is null

)

select * from orphans
