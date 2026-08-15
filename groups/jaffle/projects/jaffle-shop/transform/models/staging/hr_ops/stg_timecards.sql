with

source as (

    select * from {{ source('hr_ops', 'raw_timecards') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as timecard_id,
        cast(employee_id as varchar) as employee_id,
        cast(store_id as varchar) as location_id,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'work_date') }} as work_date,
        clock_in,
        clock_out,

        ---------- numerics
        hours_worked,
        break_minutes,

        ---------- text
        status as timecard_status

    from source

)

select * from renamed
