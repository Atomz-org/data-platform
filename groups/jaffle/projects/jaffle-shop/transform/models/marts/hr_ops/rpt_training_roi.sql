with

training as (

    select * from {{ ref('int_training_progress') }}

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

training_performance as (

    select
        employees.employee_id,
        employees.full_name,
        employees.department_name,
        employees.position_title,
        employees.is_active,
        employees.tenure_days,
        employees.tenure_bucket,
        training.total_courses_completed,
        training.required_courses_completed,
        training.total_required_courses,
        training.required_completion_pct,
        training.avg_completion_score,
        latest_performance.latest_score,
        latest_performance.rolling_avg_score,
        latest_performance.trend_direction,
        case
            when training.required_completion_pct >= 100 then 'fully_compliant'
            when training.required_completion_pct >= 75 then 'mostly_compliant'
            when training.required_completion_pct >= 50 then 'partially_compliant'
            else 'non_compliant'
        end as compliance_tier

    from employees
    left join training
        on employees.employee_id = training.employee_id
    left join latest_performance
        on employees.employee_id = latest_performance.employee_id
    where employees.is_active

),

roi_by_compliance as (

    select
        compliance_tier,
        count(*) as employee_count,
        round(avg(latest_score), 2) as avg_performance_score,
        round(avg(rolling_avg_score), 2) as avg_rolling_performance,
        round(avg(total_courses_completed), 1) as avg_courses_completed,
        round(avg(avg_completion_score), 1) as avg_training_score,
        round(avg(tenure_days), 0) as avg_tenure_days,
        sum(case when trend_direction = 'improving' then 1 else 0 end) as improving_count,
        sum(case when trend_direction = 'declining' then 1 else 0 end) as declining_count,
        sum(case when trend_direction = 'stable' then 1 else 0 end) as stable_count,
        case
            when count(*) > 0
                then round(
                    (sum(case when trend_direction = 'improving' then 1 else 0 end) * 100.0
                    / count(*)), 1
                )
            else 0
        end as improving_pct

    from training_performance
    group by compliance_tier

)

select * from roi_by_compliance
