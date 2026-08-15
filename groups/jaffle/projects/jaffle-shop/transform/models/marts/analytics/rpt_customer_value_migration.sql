with

rfm as (

    select * from {{ ref('int_customer_rfm_scores') }}

),

orders as (

    select
        order_id,
        customer_id,
        ordered_at,
        order_total
    from {{ ref('stg_orders') }}

),

monthly_customer_spend as (

    select
        customer_id,
        {{ dbt.date_trunc('month', 'ordered_at') }} as spend_month,
        sum(order_total) as monthly_spend,
        count(order_id) as monthly_orders
    from orders
    group by 1, 2

),

spend_segments as (

    select
        customer_id,
        spend_month,
        monthly_spend,
        monthly_orders,
        case
            when monthly_spend >= 100 then 'high_value'
            when monthly_spend >= 30 then 'medium_value'
            else 'low_value'
        end as value_segment,
        lag(case
            when monthly_spend >= 100 then 'high_value'
            when monthly_spend >= 30 then 'medium_value'
            else 'low_value'
        end) over (partition by customer_id order by spend_month) as prev_segment
    from monthly_customer_spend

),

migrations as (

    select
        spend_month,
        prev_segment,
        value_segment as current_segment,
        count(distinct customer_id) as customer_count,
        sum(monthly_spend) as total_spend
    from spend_segments
    where prev_segment is not null
    group by 1, 2, 3

)

select * from migrations
