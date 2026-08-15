with

payment_transactions as (

    select * from {{ ref('stg_payment_transactions') }}

),

order_payment_mix as (

    select
        order_id,
        payment_method,
        count(payment_transaction_id) as transaction_count,
        sum(payment_amount) as method_total,
        sum(
            case when payment_status = 'completed' then payment_amount else 0 end
        ) as completed_amount,
        sum(
            case when payment_status = 'failed' then payment_amount else 0 end
        ) as failed_amount,
        min(processed_date) as first_payment_date,
        max(processed_date) as last_payment_date

    from payment_transactions
    group by 1, 2

)

select * from order_payment_mix
