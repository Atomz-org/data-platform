with 

shifts as (
    select * from {{ ref('fct_shifts') }}
),

timecards as (
    select * from {{ ref('fct_timecards') }}
),

shift_data as (
    select
        shift_id,
        employee_id,
        location_id as store_id,
        scheduled_start,
        scheduled_end,
        scheduled_hours,
        actual_hours
    from shifts
),

timecard_data as (
    select
        timecard_id,
        employee_id,
        location_id as store_id,
        clock_in,
        clock_out,
        hours_worked,
        break_minutes,
        work_date
    from timecards
),

weekly_hours as (
    select
        employee_id,
        store_id,
        {{ dbt.date_trunc('week', 'work_date') }} as week_start,
        sum(hours_worked) as weekly_hours_worked
    from timecard_data
    group by 1, 2, 3
),

violations as (
    select
        employee_id,
        store_id,
        week_start,
        weekly_hours_worked,
        case
            when weekly_hours_worked > 40 then 'overtime_violation'
            else null
        end as violation_type
    from weekly_hours
    where weekly_hours_worked > 40
)

select * from violations
