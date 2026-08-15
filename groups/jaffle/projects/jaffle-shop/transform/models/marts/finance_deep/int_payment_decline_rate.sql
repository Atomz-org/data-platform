with

payments as (

    select * from {{ ref('stg_payment_transactions') }}

),

orders as (

    select
        order_id,
        location_id
    from {{ ref('stg_orders') }}

),

payment_with_store as (

    select
        p.payment_transaction_id,
        p.payment_method,
        p.payment_status,
        p.payment_amount,
        p.processed_date,
        o.location_id
    from payments as p
    left join orders as o
        on p.order_id = o.order_id

),

final as (

    select
        location_id,
        payment_method,
        processed_date,
        count(payment_transaction_id) as total_attempts,
        count(case when payment_status = 'completed' then 1 end) as successful_payments,
        count(case when payment_status in ('failed', 'declined') then 1 end) as declined_payments,
        case
            when count(payment_transaction_id) > 0
                then round(cast(
                    count(case when payment_status in ('failed', 'declined') then 1 end) * 100.0
                    / count(payment_transaction_id)
                as {{ dbt.type_float() }}), 2)
            else 0
        end as decline_rate_pct
    from payment_with_store
    group by 1, 2, 3

)

select * from final
