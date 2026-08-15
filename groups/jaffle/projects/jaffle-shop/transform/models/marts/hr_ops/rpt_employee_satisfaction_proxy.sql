with

tenure as (

    select * from {{ ref('int_employee_tenure') }}

),

overtime as (

    select * from {{ ref('int_overtime_hours') }}

),

performance as (

    select * from {{ ref('int_performance_trend') }}

),

employees as (

    select * from {{ ref('dim_employees') }}

),

latest_performance as (

    select
        employee_id,
        overall_score as latest_score,
        rolling_avg_score,
        trend_direction

    from performance
    where review_recency_rank = 1

),

employee_overtime_summary as (

    select
        employee_id,
        sum(total_overtime_hours) as total_overtime_hours,
        count(distinct week_start) as weeks_tracked,
        round(avg(total_overtime_hours), 1) as avg_weekly_overtime,
        sum(case when total_overtime_hours > 0 then 1 else 0 end) as weeks_with_overtime

    from overtime
    group by employee_id

),

satisfaction_proxy as (

    select
        employees.employee_id,
        employees.full_name,
        employees.department_name,
        employees.position_title,
        employees.location_id,
        employees.is_active,
        tenure.tenure_days,
        tenure.tenure_months,
        tenure.tenure_bucket,
        coalesce(employee_overtime_summary.avg_weekly_overtime, 0) as avg_weekly_overtime,
        coalesce(employee_overtime_summary.weeks_with_overtime, 0) as weeks_with_overtime,
        coalesce(employee_overtime_summary.weeks_tracked, 0) as weeks_tracked,
        latest_performance.latest_score,
        latest_performance.rolling_avg_score,
        latest_performance.trend_direction,

        -- Satisfaction score components (each 0-100)
        -- Tenure score: longer tenure = higher satisfaction proxy
        case
            when tenure.tenure_months >= 60 then 100
            when tenure.tenure_months >= 24 then 75
            when tenure.tenure_months >= 12 then 50
            when tenure.tenure_months >= 6 then 25
            else 10
        end as tenure_score,

        -- Overtime score: less overtime = higher satisfaction proxy
        case
            when coalesce(employee_overtime_summary.avg_weekly_overtime, 0) = 0 then 100
            when coalesce(employee_overtime_summary.avg_weekly_overtime, 0) < 2 then 80
            when coalesce(employee_overtime_summary.avg_weekly_overtime, 0) < 5 then 60
            when coalesce(employee_overtime_summary.avg_weekly_overtime, 0) < 10 then 40
            else 20
        end as overtime_score,

        -- Performance trend score
        case
            when latest_performance.trend_direction = 'improving' then 100
            when latest_performance.trend_direction = 'stable' then 70
            when latest_performance.trend_direction = 'initial' then 50
            when latest_performance.trend_direction = 'declining' then 20
            else 50
        end as performance_trend_score

    from employees
    left join tenure
        on employees.employee_id = tenure.employee_id
    left join employee_overtime_summary
        on employees.employee_id = employee_overtime_summary.employee_id
    left join latest_performance
        on employees.employee_id = latest_performance.employee_id
    where employees.is_active

),

final as (

    select
        employee_id,
        full_name,
        department_name,
        position_title,
        location_id,
        tenure_months,
        tenure_bucket,
        avg_weekly_overtime,
        latest_score,
        trend_direction,
        tenure_score,
        overtime_score,
        performance_trend_score,
        round(tenure_score + overtime_score + performance_trend_score / 3.0, 1) as composite_satisfaction_score,
        case
            when (tenure_score + overtime_score + performance_trend_score) / 3.0 >= 75 then 'high'
            when (tenure_score + overtime_score + performance_trend_score) / 3.0 >= 50 then 'moderate'
            else 'low'
        end as satisfaction_tier

    from satisfaction_proxy

)

select * from final
