with

completions as (
    select * from {{ ref('stg_training_completions') }}
),

courses as (
    select training_course_id, course_name, course_category, duration_hours from {{ ref('stg_training_courses') }}
),

final as (
    select
        tc.training_completion_id,
        tc.employee_id,
        tc.training_course_id,
        c.course_name,
        c.course_category,
        c.duration_hours as expected_duration,
        tc.started_date,
        tc.completed_date,
        tc.completion_score
    from completions as tc
    left join courses as c on tc.training_course_id = c.training_course_id
)

select * from final
