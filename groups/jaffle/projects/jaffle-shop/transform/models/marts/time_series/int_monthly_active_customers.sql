with

daily_activity as (

    select * from {{ ref('int_daily_customer_activity') }}

),

monthly_agg as (

    select
        {{ dbt.date_trunc('month', 'activity_date') }} as month_start,
        sum(unique_customers) as total_customer_visits,
        sum(total_orders) as total_orders,
        sum(total_revenue) as total_revenue,
        sum(new_customers) as new_customers,
        sum(returning_customers) as returning_customer_visits,
        count(activity_date) as active_days_in_month,
        avg(unique_customers) as avg_daily_customers

    from daily_activity
    group by 1

),

with_change as (

    select
        *,
        lag(total_customer_visits) over (
            order by month_start
        ) as prev_month_customer_visits,
        lag(new_customers) over (
            order by month_start
        ) as prev_month_new_customers,
        case
            when lag(total_customer_visits) over (order by month_start) > 0
            then (total_customer_visits - lag(total_customer_visits) over (
                order by month_start
            ))::float / lag(total_customer_visits) over (
                order by month_start
            )
        end as mom_customer_visit_change,
        case
            when lag(new_customers) over (order by month_start) > 0
            then (new_customers - lag(new_customers) over (
                order by month_start
            ))::float / lag(new_customers) over (
                order by month_start
            )
        end as mom_new_customer_change

    from monthly_agg

)

select * from with_change
