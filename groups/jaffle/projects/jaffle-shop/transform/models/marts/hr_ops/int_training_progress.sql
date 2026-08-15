with

completions as (

    select * from {{ ref('stg_training_completions') }}

),

courses as (

    select * from {{ ref('stg_training_courses') }}

),

required_courses as (

    select
        training_course_id,
        course_name,
        course_category

    from courses
    where is_required and is_active

),

employee_completions as (

    select
        completions.employee_id,
        completions.training_course_id,
        courses.course_name,
        courses.course_category,
        courses.is_required,
        completions.completion_status,
        completions.completion_score,
        completions.completed_date

    from completions
    inner join courses
        on completions.training_course_id = courses.training_course_id

),

employee_progress as (

    select
        employee_id,
        count(distinct training_course_id) as total_courses_attempted,
        count(distinct case when completion_status = 'completed' then training_course_id end) as total_courses_completed,
        count(distinct case when is_required and completion_status = 'completed' then training_course_id end) as required_courses_completed,
        (select count(*) from required_courses) as total_required_courses,
        avg(case when completion_status = 'completed' then completion_score end) as avg_completion_score,
        max(completed_date) as last_completion_date

    from employee_completions
    group by employee_id

),

final as (

    select
        employee_id,
        total_courses_attempted,
        total_courses_completed,
        required_courses_completed,
        total_required_courses,
        case
            when total_required_courses > 0
                then round(required_courses_completed * 100.0 / total_required_courses, 1)
            else 0
        end as required_completion_pct,
        avg_completion_score,
        last_completion_date

    from employee_progress

)

select * from final
