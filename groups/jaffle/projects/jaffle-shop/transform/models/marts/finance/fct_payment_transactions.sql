with

payment_transactions as (

    select * from {{ ref('stg_payment_transactions') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

final as (

    select
        pt.payment_transaction_id,
        pt.order_id,
        pt.gift_card_id,
        pt.payment_method,
        pt.payment_status,
        pt.reference_number,
        pt.payment_amount,
        pt.processed_date,
        o.location_id,
        o.customer_id,
        o.order_total,
        o.ordered_at as order_date,
        case
            when pt.payment_status = 'completed' then true
            else false
        end as is_completed,
        case
            when pt.gift_card_id is not null then true
            else false
        end as is_gift_card_payment

    from payment_transactions as pt
    left join orders as o
        on pt.order_id = o.order_id

)

select * from final
