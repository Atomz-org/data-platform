with

payments as (
    select payment_method, payment_amount
    from {{ ref('fct_payment_transactions') }}
    where payment_amount > 0
),

per_method as (
    select
        payment_method,
        count(*) as txn_count,
        round(avg(payment_amount), 2) as mean_amount,
        round(percentile_cont(0.50) within group (order by payment_amount), 2) as median_amount,
        round(percentile_cont(0.75) within group (order by payment_amount), 2) as p75_amount,
        round(percentile_cont(0.90) within group (order by payment_amount), 2) as p90_amount,
        round(percentile_cont(0.99) within group (order by payment_amount), 2) as p99_amount
    from payments
    group by 1
)

select * from per_method
