with

daily as (

    select * from {{ ref('met_daily_labor_metrics') }}

),

weekly_agg as (

    select
        {{ dbt.date_trunc('week', 'work_date') }} as week_start,
        location_id,
        store_name,
        sum(total_labor_hours) as weekly_labor_hours,
        sum(total_labor_cost) as weekly_labor_cost,
        avg(employee_count) as avg_daily_employees,
        sum(order_count) as weekly_orders,
        sum(daily_revenue) as weekly_revenue,
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

)

select * from weekly_agg
