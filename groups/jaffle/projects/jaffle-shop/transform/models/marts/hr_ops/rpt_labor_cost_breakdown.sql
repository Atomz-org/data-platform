with

labor_cost as (

    select * from {{ ref('int_labor_cost_daily') }}

),

overtime as (

    select * from {{ ref('int_overtime_hours') }}

),

employees as (

    select * from {{ ref('dim_employees') }}

),

positions as (

    select * from {{ ref('dim_positions') }}

),

labor_hours as (

    select * from {{ ref('int_labor_hours_actual') }}

),

employee_labor as (

    select
        labor_hours.employee_id,
        labor_hours.location_id,
        labor_hours.work_date,
        {{ dbt.date_trunc('month', 'labor_hours.work_date') }} as work_month,
        labor_hours.total_hours_worked,
        employees.department_name,
        employees.position_title,
        employees.pay_grade,
        employees.is_active,
        positions.min_hourly_rate as hourly_rate,
        -- NOTE: cost calculation using standard rate
        labor_hours.total_hours_worked * positions.max_hourly_rate as regular_cost

    from labor_hours
    inner join employees
        on labor_hours.employee_id = employees.employee_id
    inner join positions
        on employees.position_id = positions.position_id

),

employee_overtime as (

    select
        employee_id,
        location_id,
        week_start,
        total_overtime_hours,
        weekly_total_hours - total_overtime_hours as regular_hours

    from overtime

),

monthly_by_department as (

    select
        employee_labor.department_name,
        employee_labor.pay_grade,
        employee_labor.work_month,
        count(distinct employee_labor.employee_id) as employee_count,
        sum(employee_labor.total_hours_worked) as total_hours,
        sum(employee_labor.regular_cost) as total_labor_cost,
        round(avg(employee_labor.hourly_rate), 2) as avg_hourly_rate

    from employee_labor
    group by
        employee_labor.department_name,
        employee_labor.pay_grade,
        employee_labor.work_month

),

overtime_by_department as (

    select
        employees.department_name,
        {{ dbt.date_trunc('month', 'employee_overtime.week_start') }} as work_month,
        sum(employee_overtime.total_overtime_hours) as overtime_hours,
        sum(employee_overtime.regular_hours) as regular_hours

    from employee_overtime
    inner join employees
        on employee_overtime.employee_id = employees.employee_id
    group by
        employees.department_name,
        {{ dbt.date_trunc('month', 'employee_overtime.week_start') }}

),

final as (

    select
        monthly_by_department.department_name,
        monthly_by_department.pay_grade,
        monthly_by_department.work_month,
        monthly_by_department.employee_count,
        monthly_by_department.total_hours,
        monthly_by_department.total_labor_cost,
        monthly_by_department.avg_hourly_rate,
        coalesce(overtime_by_department.overtime_hours, 0) as overtime_hours,
        coalesce(overtime_by_department.regular_hours, 0) as regular_hours,
        case
            when monthly_by_department.total_hours > 0
                then round(
                    (coalesce(overtime_by_department.overtime_hours, 0) * 100.0
                    / monthly_by_department.total_hours), 1
                )
            else 0
        end as overtime_pct

    from monthly_by_department
    left join overtime_by_department
        on monthly_by_department.department_name = overtime_by_department.department_name
        and monthly_by_department.work_month = overtime_by_department.work_month

)

select * from final
