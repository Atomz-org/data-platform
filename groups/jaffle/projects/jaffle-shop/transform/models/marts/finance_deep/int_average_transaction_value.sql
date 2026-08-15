with

orders as (

    select * from {{ ref('stg_orders') }}

),

daily_atv as (

    select
        location_id,
        ordered_at as transaction_date,
        count(order_id) as daily_order_count,
        sum(order_total) as daily_total_revenue,
        avg(order_total) as avg_transaction_value,
        min(order_total) as min_transaction_value,
        max(order_total) as max_transaction_value
    from orders
    group by 1, 2

),

with_trend as (

    select
        location_id,
        transaction_date,
        daily_order_count,
        daily_total_revenue,
        avg_transaction_value,
        min_transaction_value,
        max_transaction_value,
        avg(avg_transaction_value) over (
            partition by location_id
            order by transaction_date
            rows between 6 preceding and current row
        ) as rolling_7d_avg_atv,
        avg(avg_transaction_value) over (
            partition by location_id
            order by transaction_date
            rows between 29 preceding and current row
        ) as rolling_30d_avg_atv
    from daily_atv

)

select * from with_trend
