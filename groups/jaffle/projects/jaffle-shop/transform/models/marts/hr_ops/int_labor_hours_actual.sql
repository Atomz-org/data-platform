with

timecards as (

    select * from {{ ref('stg_timecards') }}
    where timecard_status = 'approved'

),

daily_hours as (

    select
        employee_id,
        location_id,
        work_date,
        sum(hours_worked) as total_hours_worked,
        sum(break_minutes) as total_break_minutes,
        count(*) as timecard_entries

    from timecards
    group by
        employee_id,
        location_id,
        work_date

)

select * from daily_hours
