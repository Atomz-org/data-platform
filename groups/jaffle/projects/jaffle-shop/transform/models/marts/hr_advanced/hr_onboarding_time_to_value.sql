with

employees as (
    select
        employee_id,
        full_name,
        department_name,
        hire_date
    from {{ ref('dim_employees') }}
),

productivity as (
    select
        employee_id,
        work_date,
        orders_handled,
        total_hours_worked
    from {{ ref('int_employee_productivity') }}
),

dept_avg_productivity as (
    select
        e.department_name,
        avg(p.orders_handled) as dept_avg_orders
    from productivity as p
    inner join employees as e on p.employee_id = e.employee_id
    group by 1
),

employee_monthly as (
    select
        p.employee_id,
        {{ dbt.date_trunc('month', 'p.work_date') }} as work_month,
        sum(p.orders_handled) as monthly_orders,
        sum(p.total_hours_worked) as monthly_hours,
        case when sum(p.total_hours_worked) > 0
            then sum(p.orders_handled) * 1.0 / sum(p.total_hours_worked)
            else 0
        end as orders_per_hour
    from productivity as p
    group by 1, 2
),

employee_ramp as (
    select
        e.employee_id,
        e.full_name,
        e.department_name,
        e.hire_date,
        em.work_month,
        em.monthly_orders,
        em.orders_per_hour,
        dap.dept_avg_orders,
        {{ dbt.datediff('e.hire_date', 'em.work_month', 'month') }} as months_since_hire,
        case
            when em.orders_per_hour >= dap.dept_avg_orders then true
            else false
        end as reached_dept_avg
    from employees as e
    inner join employee_monthly as em on e.employee_id = em.employee_id
    inner join dept_avg_productivity as dap on e.department_name = dap.department_name
),

time_to_value as (
    select
        employee_id,
        full_name,
        department_name,
        hire_date,
        min(case when reached_dept_avg then months_since_hire end) as months_to_dept_avg
    from employee_ramp
    group by 1, 2, 3, 4
)

select
    *,
    case
        when months_to_dept_avg <= 3 then 'fast_ramp'
        when months_to_dept_avg <= 6 then 'normal_ramp'
        when months_to_dept_avg is not null then 'slow_ramp'
        else 'not_yet_reached'
    end as ramp_category
from time_to_value
