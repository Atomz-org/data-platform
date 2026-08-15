with

payments as (
    select * from {{ ref('stg_payment_transactions') }}
),

orders as (
    select order_id, customer_id, location_id, ordered_at from {{ ref('stg_orders') }}
),

final as (
    select
        pt.payment_transaction_id,
        pt.order_id,
        o.customer_id,
        o.location_id,
        o.ordered_at,
        pt.payment_method,
        pt.payment_amount,
        pt.processed_date,
        pt.payment_status
    from payments as pt
    left join orders as o on pt.order_id = o.order_id
)

select * from final
