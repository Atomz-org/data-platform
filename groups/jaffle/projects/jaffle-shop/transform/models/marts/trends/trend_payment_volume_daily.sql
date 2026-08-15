with

daily_payments as (
    select
        processed_date,
        payment_method,
        count(*) as transaction_count,
        sum(payment_amount) as total_amount
    from {{ ref('fct_payment_transactions') }}
    group by 1, 2
),

trended as (
    select
        processed_date,
        payment_method,
        transaction_count,
        total_amount,
        avg(transaction_count) over (
            partition by payment_method order by processed_date
            rows between 6 preceding and current row
        ) as txn_count_7d_ma,
        avg(total_amount) over (
            partition by payment_method order by processed_date
            rows between 6 preceding and current row
        ) as amount_7d_ma,
        lag(transaction_count, 7) over (partition by payment_method order by processed_date) as txn_same_day_last_week
    from daily_payments
)

select * from trended
