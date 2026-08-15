with

completions as (

    select * from {{ ref('stg_training_completions') }}

),

courses as (

    select
        training_course_id,
        course_name,
        course_category,
        duration_hours
    from {{ ref('stg_training_courses') }}

),

final as (

    select
        c.training_course_id,
        c.course_name,
        c.course_category,
        c.duration_hours as expected_duration_hours,
        count(tc.training_completion_id) as total_enrollments,
        count(case when tc.completion_status = 'completed' then 1 end) as completed_count,
        avg(case
            when tc.completed_date is not null and tc.started_date is not null
                then {{ dbt.datediff('tc.started_date', 'tc.completed_date', 'day') }}
            else null
        end) as avg_days_to_complete,
        min(case
            when tc.completed_date is not null and tc.started_date is not null
                then {{ dbt.datediff('tc.started_date', 'tc.completed_date', 'day') }}
            else null
        end) as min_days_to_complete,
        max(case
            when tc.completed_date is not null and tc.started_date is not null
                then {{ dbt.datediff('tc.started_date', 'tc.completed_date', 'day') }}
            else null
        end) as max_days_to_complete,
        avg(tc.completion_score) as avg_completion_score
    from courses as c
    left join completions as tc
        on c.training_course_id = tc.training_course_id
    group by 1, 2, 3, 4

)

select * from final
