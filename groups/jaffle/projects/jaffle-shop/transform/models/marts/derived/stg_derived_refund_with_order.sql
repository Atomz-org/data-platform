with

refunds as (
    select * from {{ ref('stg_refunds') }}
),

orders as (
    select order_id, customer_id, location_id, order_total from {{ ref('stg_orders') }}
),

final as (
    select
        r.refund_id,
        r.order_id,
        o.customer_id,
        o.location_id,
        o.order_total,
        r.requested_date,
        r.refund_amount,
        r.refund_reason,
        round(r.refund_amount * 100.0 / nullif(o.order_total, 0), 2) as refund_pct_of_order
    from refunds as r
    left join orders as o on r.order_id = o.order_id
)

select * from final
