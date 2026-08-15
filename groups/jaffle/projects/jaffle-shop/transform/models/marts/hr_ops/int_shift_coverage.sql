with

shifts as (

    select * from {{ ref('stg_shifts') }}

),

store_hours as (

    select * from {{ ref('stg_store_hours') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

scheduled_coverage as (

    select
        shifts.location_id,
        shifts.shift_date,
        locations.location_name,
        count(distinct shifts.employee_id) as scheduled_staff_count,
        sum(shifts.scheduled_hours) as total_scheduled_hours

    from shifts
    inner join locations
        on shifts.location_id = locations.location_id
    group by
        shifts.location_id,
        shifts.shift_date,
        locations.location_name

),

required_coverage as (

    select
        store_hours.location_id,
        store_hours.day_of_week,
        store_hours.day_name,
        store_hours.open_time,
        store_hours.close_time,
        store_hours.is_closed

    from store_hours
    where not store_hours.is_closed

),

final as (

    select
        scheduled_coverage.location_id,
        scheduled_coverage.location_name,
        scheduled_coverage.shift_date,
        scheduled_coverage.scheduled_staff_count,
        scheduled_coverage.total_scheduled_hours,
        required_coverage.open_time,
        required_coverage.close_time,
        required_coverage.is_closed

    from scheduled_coverage
    left join required_coverage
        on scheduled_coverage.location_id = required_coverage.location_id
        and {{ day_of_week_number('scheduled_coverage.shift_date') }} = required_coverage.day_of_week

)

select * from final
