with

orders as (

    select * from {{ ref('stg_orders') }}

),

monthly_orders as (

    select
        customer_id,
        {{ dbt.date_trunc('month', 'ordered_at') }} as order_month,
        count(distinct order_id) as monthly_order_count,
        sum(order_total) as monthly_spend
    from orders
    group by 1, 2

),

with_moving_avg as (

    select
        customer_id,
        order_month,
        monthly_order_count,
        monthly_spend,

        -- 3-month moving average
        round(
            (avg(monthly_order_count) over (
                partition by customer_id
                order by order_month
                rows between 2 preceding and current row
            )), 2
        ) as order_count_3m_avg,

        -- Prior month
        lag(monthly_order_count, 1) over (
            partition by customer_id
            order by order_month
        ) as prior_month_orders,

        -- 3-month ago
        lag(monthly_order_count, 3) over (
            partition by customer_id
            order by order_month
        ) as three_months_ago_orders,

        -- Row number for recency
        row_number() over (
            partition by customer_id
            order by order_month desc
        ) as months_ago

    from monthly_orders

),

with_trend as (

    select
        customer_id,
        order_month,
        monthly_order_count,
        monthly_spend,
        order_count_3m_avg,
        prior_month_orders,

        -- Acceleration: compare current 3m avg to prior 3m avg
        case
            when three_months_ago_orders is not null
                and lag(order_count_3m_avg, 3) over (
                    partition by customer_id order by order_month
                ) > 0
            then round(
                (order_count_3m_avg - lag(order_count_3m_avg, 3) over (
                    partition by customer_id order by order_month
                )) / lag(order_count_3m_avg, 3) over (
                    partition by customer_id order by order_month
                ), 4
            )
            else null
        end as trend_acceleration,

        case
            when monthly_order_count > coalesce(prior_month_orders, 0) then 'accelerating'
            when monthly_order_count < coalesce(prior_month_orders, 0) then 'decelerating'
            else 'stable'
        end as monthly_trend_direction

    from with_moving_avg

)

select * from with_trend
