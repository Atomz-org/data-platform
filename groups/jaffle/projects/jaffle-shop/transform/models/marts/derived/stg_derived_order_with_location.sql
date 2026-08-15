with

orders as (
    select * from {{ ref('stg_orders') }}
),

locations as (
    select location_id, location_name from {{ ref('stg_locations') }}
),

final as (
    select
        o.order_id,
        o.customer_id,
        o.location_id,
        l.location_name,
        o.ordered_at,
        o.order_total,
        o.tax_paid,
        o.subtotal
    from orders as o
    left join locations as l on o.location_id = l.location_id
)

select * from final
