with

labor_cost as (

    select * from {{ ref('int_labor_cost_daily') }}

),

orders as (

    select
        location_id,
        ordered_at as order_date,
        sum(order_total) as daily_revenue

    from {{ ref('stg_orders') }}
    group by
        location_id,
        ordered_at

),

daily_efficiency as (

    select
        labor_cost.location_id,
        labor_cost.work_date,
        labor_cost.total_hours,
        labor_cost.total_labor_cost,
        labor_cost.employee_count,
        coalesce(orders.daily_revenue, 0) as daily_revenue,
        case
            when coalesce(orders.daily_revenue, 0) > 0
                then round(labor_cost.total_labor_cost / orders.daily_revenue * 100, 1)
            else null
        end as labor_cost_pct_of_revenue,
        case
            when labor_cost.total_hours > 0
                then round(coalesce(orders.daily_revenue, 0) / labor_cost.total_hours, 2)
            else null
        end as revenue_per_labor_hour

    from labor_cost
    left join orders
        on labor_cost.location_id = orders.location_id
        and labor_cost.work_date = orders.order_date

),

monthly_summary as (

    select
        location_id,
        {{ dbt.date_trunc('month', 'work_date') }} as report_month,
        sum(total_hours) as monthly_labor_hours,
        sum(total_labor_cost) as monthly_labor_cost,
        sum(daily_revenue) as monthly_revenue,
        case
            when sum(daily_revenue) > 0
                then round(sum(total_labor_cost) / sum(daily_revenue) * 100, 1)
            else null
        end as monthly_labor_cost_pct,
        case
            when sum(total_hours) > 0
                then round(sum(daily_revenue) / sum(total_hours), 2)
            else null
        end as monthly_revenue_per_labor_hour,
        avg(employee_count) as avg_daily_staff_count

    from daily_efficiency
    group by
        location_id,
        {{ dbt.date_trunc('month', 'work_date') }}

)

select * from monthly_summary
