with

training_progress as (

    select * from {{ ref('int_training_progress') }}

),

employee_performance as (

    select
        employee_id,
        performance_score,
        performance_tier
    from {{ ref('scr_employee_performance') }}

),

employees as (

    select
        employee_id,
        full_name,
        hire_date,
        termination_date,
        location_id
    from {{ ref('dim_employees') }}

),

training_completions as (

    select
        employee_id,
        count(training_completion_id) as total_completions,
        avg(completion_score) as avg_training_score
    from {{ ref('stg_training_completions') }}
    where completion_status = 'completed'
    group by 1

),

final as (

    select
        e.employee_id,
        e.full_name,
        tp.total_required_courses,
        tp.required_courses_completed,
        tp.required_completion_pct,
        coalesce(tc.total_completions, 0) as total_courses_completed,
        tc.avg_training_score,
        ep.performance_score,
        ep.performance_tier,
        case when e.termination_date is null then 'retained' else 'departed' end as retention_status,
        case
            when coalesce(tc.total_completions, 0) >= 10 and ep.performance_tier = 'high' then 'high_roi'
            when coalesce(tc.total_completions, 0) >= 5 then 'moderate_roi'
            when coalesce(tc.total_completions, 0) > 0 then 'low_roi'
            else 'no_training'
        end as training_roi_tier
    from employees as e
    left join training_progress as tp
        on e.employee_id = tp.employee_id
    left join training_completions as tc
        on e.employee_id = tc.employee_id
    left join employee_performance as ep
        on e.employee_id = ep.employee_id

)

select * from final
