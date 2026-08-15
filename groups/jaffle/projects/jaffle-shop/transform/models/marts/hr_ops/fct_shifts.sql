with

shifts as (

    select * from {{ ref('stg_shifts') }}

),

employees as (

    select * from {{ ref('int_employee_enriched') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

final as (

    select
        shifts.shift_id,
        shifts.employee_id,
        shifts.location_id,
        employees.full_name as full_name,
        employees.department_name,
        employees.position_title,
        locations.location_name,
        shifts.shift_date,
        shifts.shift_type,
        shifts.shift_status,
        shifts.scheduled_start,
        shifts.scheduled_end,
        shifts.actual_start,
        shifts.actual_end,
        shifts.scheduled_hours,
        case
            when shifts.actual_start is not null and shifts.actual_end is not null
                then {{ dbt.datediff('shifts.actual_start', 'shifts.actual_end', 'hour') }}
            else null
        end as actual_hours,
        case
            when shifts.shift_status = 'no_show' then true
            else false
        end as is_no_show,
        case
            when shifts.actual_start > shifts.scheduled_start then true
            else false
        end as is_late_arrival

    from shifts
    left join employees
        on shifts.employee_id = employees.employee_id
    left join locations
        on shifts.location_id = locations.location_id

)

select * from final
