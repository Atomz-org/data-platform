with

shifts as (

    select * from {{ ref('stg_shifts') }}

),

shift_patterns as (

    select
        employee_id,
        location_id,
        count(shift_id) as total_shifts,
        count(case when shift_type = 'morning' then 1 end) as morning_count,
        count(case when shift_type = 'afternoon' then 1 end) as afternoon_count,
        count(case when shift_type = 'evening' then 1 end) as evening_count,
        sum(scheduled_hours) as total_scheduled_hours,
        avg(scheduled_hours) as avg_shift_hours
    from shifts
    where shift_status = 'scheduled'
    group by 1, 2

),

final as (

    select
        employee_id,
        location_id,
        total_shifts,
        morning_count,
        afternoon_count,
        evening_count,
        total_scheduled_hours,
        avg_shift_hours,
        case
            when morning_count >= afternoon_count and morning_count >= evening_count then 'morning_primary'
            when afternoon_count >= morning_count and afternoon_count >= evening_count then 'afternoon_primary'
            else 'evening_primary'
        end as primary_shift_pattern,
        case
            when morning_count > 0 and afternoon_count > 0 and evening_count > 0 then 'all_shifts'
            when (morning_count > 0 and afternoon_count > 0) or (morning_count > 0 and evening_count > 0) or (afternoon_count > 0 and evening_count > 0) then 'mixed'
            else 'single_shift_type'
        end as shift_variety
    from shift_patterns

)

select * from final
