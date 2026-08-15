with

courses as (

    select * from {{ ref('stg_training_courses') }}

),

final as (

    select
        training_course_id,
        course_name,
        course_description,
        course_category,
        duration_hours,
        is_required,
        is_active

    from courses

)

select * from final
