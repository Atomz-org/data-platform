with

source as (

    select * from {{ source('hr_ops', 'raw_store_hours') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as store_hours_id,
        cast(store_id as varchar) as location_id,

        ---------- numerics
        day_of_week,

        ---------- text
        case day_of_week
            when 0 then 'Sunday'
            when 1 then 'Monday'
            when 2 then 'Tuesday'
            when 3 then 'Wednesday'
            when 4 then 'Thursday'
            when 5 then 'Friday'
            when 6 then 'Saturday'
        end as day_name,

        ---------- timestamps
        open_time,
        close_time,

        ---------- booleans
        is_closed

    from source

)

select * from renamed
