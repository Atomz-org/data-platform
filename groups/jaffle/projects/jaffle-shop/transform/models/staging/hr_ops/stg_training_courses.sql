with

source as (

    select * from {{ source('hr_ops', 'raw_training_courses') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as training_course_id,

        ---------- text
        name as course_name,
        description as course_description,
        category as course_category,

        ---------- numerics
        duration_hours,

        ---------- booleans
        is_required,
        is_active

    from source

)

select * from renamed
