with

source as (

    select * from {{ source('hr_ops', 'raw_training_completions') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as training_completion_id,
        cast(employee_id as varchar) as employee_id,
        cast(course_id as varchar) as training_course_id,

        ---------- text
        status as completion_status,

        ---------- numerics
        score as completion_score,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'started_at') }} as started_date,
        {{ dbt.date_trunc('day', 'completed_at') }} as completed_date

    from source

)

select * from renamed
