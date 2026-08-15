with

productivity as (

    select * from {{ ref('int_employee_productivity') }}

),

employees as (

    select * from {{ ref('dim_employees') }}

),

employee_avg_productivity as (

    select
        productivity.employee_id,
        employees.full_name,
        employees.department_name,
        employees.position_title,
        employees.location_id,
        employees.is_active,
        count(distinct work_date) as days_worked,
        sum(total_hours_worked) as total_hours_worked,
        sum(orders_handled) as total_orders_handled,
        case
            when sum(total_hours_worked) > 0
                then round(
                    (sum(orders_handled) * 1.0
                    / sum(total_hours_worked)), 2
                )
            else 0
        end as avg_orders_per_hour,
        round(avg(orders_per_hour), 2) as daily_avg_orders_per_hour

    from productivity
    inner join employees
        on productivity.employee_id = employees.employee_id
    group by
        productivity.employee_id,
        employees.full_name,
        employees.department_name,
        employees.position_title,
        employees.location_id,
        employees.is_active

),

ranked as (

    select
        employee_id,
        full_name,
        department_name,
        position_title,
        location_id,
        is_active,
        days_worked,
        total_hours_worked,
        total_orders_handled,
        avg_orders_per_hour,
        daily_avg_orders_per_hour,
        rank() over (
            order by avg_orders_per_hour desc
        ) as overall_productivity_rank,
        rank() over (
            partition by department_name
            order by avg_orders_per_hour desc
        ) as department_productivity_rank,
        case
            when avg_orders_per_hour >= (
                select percentile_cont(0.75) within group (order by avg_orders_per_hour)
                from employee_avg_productivity
            ) then 'high_performer'
            when avg_orders_per_hour >= (
                select percentile_cont(0.25) within group (order by avg_orders_per_hour)
                from employee_avg_productivity
            ) then 'average_performer'
            else 'needs_improvement'
        end as performance_tier

    from employee_avg_productivity

)

select * from ranked
