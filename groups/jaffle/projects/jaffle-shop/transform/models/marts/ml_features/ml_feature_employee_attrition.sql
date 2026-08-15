with

employees as (

    select * from {{ ref('dim_employees') }}

),

productivity as (

    select
        employee_id,
        avg(orders_per_hour) as avg_orders_per_hour,
        avg(total_hours_worked) as avg_daily_hours,
        count(distinct work_date) as total_work_days
    from {{ ref('int_employee_productivity') }}
    group by 1

),

overtime as (

    select
        employee_id,
        sum(total_overtime_hours) as total_overtime_hours,
        count(distinct week_start) as weeks_tracked,
        sum(total_overtime_hours) * 1.0
            / nullif(count(distinct week_start), 0) as avg_weekly_overtime,
        count(distinct case when total_overtime_hours > 0 then week_start end) as weeks_with_overtime
    from {{ ref('int_overtime_hours') }}
    group by 1

),

training as (

    select
        employee_id,
        total_courses_completed,
        required_completion_pct,
        avg_completion_score
    from {{ ref('int_training_progress') }}

),

features as (

    select
        e.employee_id,
        e.department_name,
        e.position_title,
        e.is_management,
        e.pay_grade,
        e.location_id,

        -- Tenure
        e.tenure_days,
        e.tenure_months,
        e.tenure_bucket,

        -- Productivity
        coalesce(p.avg_orders_per_hour, 0) as avg_orders_per_hour,
        coalesce(p.avg_daily_hours, 0) as avg_daily_hours,
        coalesce(p.total_work_days, 0) as total_work_days,

        -- Overtime
        coalesce(ot.total_overtime_hours, 0) as total_overtime_hours,
        coalesce(ot.avg_weekly_overtime, 0) as avg_weekly_overtime,
        case
            when ot.weeks_tracked > 0
            then round(ot.weeks_with_overtime * 100.0 / ot.weeks_tracked, 2)
            else 0
        end as overtime_frequency_pct,

        -- Training
        coalesce(t.total_courses_completed, 0) as courses_completed,
        coalesce(t.required_completion_pct, 0) as training_completion_pct,
        coalesce(t.avg_completion_score, 0) as avg_training_score,

        -- Target: has the employee departed?
        case when e.is_active then 0 else 1 end as attrition_label

    from employees as e
    left join productivity as p
        on e.employee_id = p.employee_id
    left join overtime as ot
        on e.employee_id = ot.employee_id
    left join training as t
        on e.employee_id = t.employee_id

)

select * from features
