with

source as (

    select * from {{ source('hr_ops', 'raw_shifts') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as shift_id,
        cast(employee_id as varchar) as employee_id,
        cast(store_id as varchar) as location_id,

        ---------- text
        shift_type,
        status as shift_status,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'shift_date') }} as shift_date,
        scheduled_start,
        scheduled_end,
        actual_start,
        actual_end,

        ---------- numerics
        {{ dbt.datediff('scheduled_start', 'scheduled_end', 'hour') }} as scheduled_hours

    from source

)

select * from renamed
