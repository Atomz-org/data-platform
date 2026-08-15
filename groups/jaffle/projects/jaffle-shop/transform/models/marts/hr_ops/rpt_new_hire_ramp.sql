with

productivity as (

    select * from {{ ref('int_employee_productivity') }}

),

tenure as (

    select * from {{ ref('int_employee_tenure') }}

),

employees as (

    select * from {{ ref('dim_employees') }}

),

new_hire_productivity as (

    select
        productivity.employee_id,
        employees.full_name,
        employees.department_name,
        employees.position_title,
        employees.hire_date,
        tenure.tenure_days,
        tenure.tenure_months,
        work_date,
        total_hours_worked,
        orders_handled,
        orders_per_hour,
        {{ dbt.datediff('employees.hire_date', 'work_date', 'day') }} as days_since_hire,
        case
            when {{ dbt.datediff('employees.hire_date', 'work_date', 'day') }} <= 30 then 'month_1'
            when {{ dbt.datediff('employees.hire_date', 'work_date', 'day') }} <= 60 then 'month_2'
            when {{ dbt.datediff('employees.hire_date', 'work_date', 'day') }} <= 90 then 'month_3'
            when {{ dbt.datediff('employees.hire_date', 'work_date', 'day') }} <= 180 then 'months_4_to_6'
            else 'after_6_months'
        end as ramp_phase

    from productivity
    inner join employees
        on productivity.employee_id = employees.employee_id
    inner join tenure
        on productivity.employee_id = tenure.employee_id

),

ramp_by_phase as (

    select
        ramp_phase,
        count(distinct employee_id) as employee_count,
        count(*) as total_work_days,
        round(avg(orders_per_hour), 2) as avg_orders_per_hour,
        round(avg(total_hours_worked), 1) as avg_daily_hours,
        round(avg(orders_handled), 1) as avg_daily_orders

    from new_hire_productivity
    group by ramp_phase

),

ramp_by_employee_phase as (

    select
        employee_id,
        full_name,
        department_name,
        position_title,
        hire_date,
        ramp_phase,
        count(*) as days_in_phase,
        round(avg(orders_per_hour), 2) as avg_orders_per_hour,
        round(avg(total_hours_worked), 1) as avg_daily_hours

    from new_hire_productivity
    group by
        employee_id,
        full_name,
        department_name,
        position_title,
        hire_date,
        ramp_phase

),

final as (

    select
        ramp_phase,
        employee_count,
        total_work_days,
        avg_orders_per_hour,
        avg_daily_hours,
        avg_daily_orders,
        lag(avg_orders_per_hour) over (
            order by case ramp_phase
                when 'month_1' then 1
                when 'month_2' then 2
                when 'month_3' then 3
                when 'months_4_to_6' then 4
                when 'after_6_months' then 5
            end
        ) as prev_phase_orders_per_hour,
        case
            when lag(avg_orders_per_hour) over (
                order by case ramp_phase
                    when 'month_1' then 1
                    when 'month_2' then 2
                    when 'month_3' then 3
                    when 'months_4_to_6' then 4
                    when 'after_6_months' then 5
                end
            ) > 0
                then round(
                    (avg_orders_per_hour - lag(avg_orders_per_hour) over (
                        order by case ramp_phase
                            when 'month_1' then 1
                            when 'month_2' then 2
                            when 'month_3' then 3
                            when 'months_4_to_6' then 4
                            when 'after_6_months' then 5
                        end
                    )) * 100.0
                    / lag(avg_orders_per_hour) over (
                        order by case ramp_phase
                            when 'month_1' then 1
                            when 'month_2' then 2
                            when 'month_3' then 3
                            when 'months_4_to_6' then 4
                            when 'after_6_months' then 5
                        end
                    ), 1
                )
            else null
        end as phase_over_phase_improvement_pct

    from ramp_by_phase

)

select * from final
