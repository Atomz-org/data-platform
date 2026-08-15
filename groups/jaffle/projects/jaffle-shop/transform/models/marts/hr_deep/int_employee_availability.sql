with

shifts as (

    select * from {{ ref('stg_shifts') }}

),

weekly_availability as (

    select
        employee_id,
        location_id,
        {{ dbt.date_trunc('week', 'shift_date') }} as week_start,
        count(shift_id) as scheduled_shifts,
        sum(scheduled_hours) as total_scheduled_hours,
        count(case when shift_type = 'morning' then 1 end) as morning_shifts,
        count(case when shift_type = 'afternoon' then 1 end) as afternoon_shifts,
        count(case when shift_type = 'evening' then 1 end) as evening_shifts
    from shifts
    where shift_status = 'scheduled'
    group by 1, 2, 3

),

final as (

    select
        employee_id,
        location_id,
        week_start,
        scheduled_shifts,
        total_scheduled_hours,
        morning_shifts,
        afternoon_shifts,
        evening_shifts,
        40.0 - total_scheduled_hours as available_hours_remaining,
        case
            when total_scheduled_hours >= 35 then 'full_time'
            when total_scheduled_hours >= 20 then 'part_time'
            else 'minimal'
        end as availability_status
    from weekly_availability

)

select * from final
