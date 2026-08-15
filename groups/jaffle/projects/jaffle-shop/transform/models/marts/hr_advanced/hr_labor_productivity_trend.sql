with

monthly_productivity as (
    select
        {{ dbt.date_trunc('month', 'work_date') }} as month_start,
        count(distinct employee_id) as active_employees,
        sum(orders_handled) as total_orders_handled,
        sum(total_hours_worked) as total_hours_worked
    from {{ ref('int_employee_productivity') }}
    group by 1
),

final as (
    select
        month_start,
        active_employees,
        total_orders_handled,
        total_hours_worked,
        case
            when total_hours_worked > 0
            then round(total_orders_handled * 1.0 / total_hours_worked, 2)
            else null
        end as orders_per_labor_hour,
        case
            when active_employees > 0
            then round(total_orders_handled * 1.0 / active_employees, 2)
            else null
        end as orders_per_employee,
        lag(total_orders_handled) over (order by month_start) as prev_month_orders,
        case
            when lag(total_orders_handled) over (order by month_start) > 0
            then round((total_orders_handled - lag(total_orders_handled) over (order by month_start)) * 100.0
                / lag(total_orders_handled) over (order by month_start), 2)
            else null
        end as mom_order_change_pct
    from monthly_productivity
)

select * from final
