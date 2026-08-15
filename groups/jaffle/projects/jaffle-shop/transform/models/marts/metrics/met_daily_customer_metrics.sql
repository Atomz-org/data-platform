with

daily_activity as (

    select * from {{ ref('int_daily_customer_activity') }}

),

final as (

    select
        activity_date,
        unique_customers as active_customers,
        new_customers,
        returning_customers,
        total_orders,
        total_revenue,
        case
            when unique_customers > 0
            then total_orders * 1.0 / unique_customers
            else 0
        end as orders_per_customer,
        case
            when unique_customers > 0
            then total_revenue / unique_customers
            else 0
        end as revenue_per_customer,

        -- 7-day rolling
        avg(new_customers) over (
            order by activity_date
            rows between 6 preceding and current row
        ) as new_customers_7d_avg,
        avg(unique_customers) over (
            order by activity_date
            rows between 6 preceding and current row
        ) as active_customers_7d_avg

    from daily_activity

)

select * from final
