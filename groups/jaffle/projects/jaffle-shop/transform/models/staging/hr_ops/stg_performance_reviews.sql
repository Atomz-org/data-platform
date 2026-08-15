with

source as (

    select * from {{ source('hr_ops', 'raw_performance_reviews') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as review_id,
        cast(employee_id as varchar) as employee_id,
        cast(reviewer_id as varchar) as reviewer_id,

        ---------- text
        review_period,
        comments as review_comments,

        ---------- numerics
        overall_score,
        attendance_score,
        quality_score,
        teamwork_score,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'review_date') }} as review_date

    from source

)

select * from renamed
