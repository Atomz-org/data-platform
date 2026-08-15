with

daily as (

    select * from {{ ref('met_daily_labor_metrics') }}

),

monthly_agg as (

    select
        {{ dbt.date_trunc('month', 'work_date') }} as month_start,
        location_id,
        store_name,
        sum(total_labor_hours) as monthly_labor_hours,
        sum(total_labor_cost) as monthly_labor_cost,
        avg(employee_count) as avg_daily_employees,
        sum(order_count) as monthly_orders,
        sum(daily_revenue) as monthly_revenue,
        case
            when sum(total_labor_hours) > 0
            then sum(order_count) * 1.0 / sum(total_labor_hours)
            else 0
        end as orders_per_labor_hour,
        case
            when sum(daily_revenue) > 0
            then sum(total_labor_cost) * 100.0 / sum(daily_revenue)
            else null
        end as labor_cost_pct_of_revenue

    from daily
    group by 1, 2, 3

),

with_change as (

    select
        *,
        lag(monthly_labor_cost) over (
            partition by location_id order by month_start
        ) as prev_month_labor_cost,
        case
            when lag(monthly_labor_cost) over (
                partition by location_id order by month_start
            ) > 0
            then (monthly_labor_cost - lag(monthly_labor_cost) over (
                partition by location_id order by month_start
            )) * 1.0 / lag(monthly_labor_cost) over (
                partition by location_id order by month_start
            )
        end as mom_labor_cost_change

    from monthly_agg

)

select * from with_change
