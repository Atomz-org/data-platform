with

orders as (
    select * from {{ ref('stg_orders') }}
),

customers as (
    select customer_id, customer_name from {{ ref('stg_customers') }}
),

final as (
    select
        o.order_id,
        o.customer_id,
        c.customer_name,
        o.location_id,
        o.ordered_at,
        o.order_total,
        o.tax_paid,
        o.subtotal
    from orders as o
    left join customers as c on o.customer_id = c.customer_id
)

select * from final
