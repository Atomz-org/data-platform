with

shifts as (

    select * from {{ ref('stg_shifts') }}

),

timecards as (

    select * from {{ ref('stg_timecards') }}

),

matched as (

    select
        s.shift_id,
        s.employee_id,
        s.location_id,
        s.shift_date,
        s.shift_type,
        s.scheduled_start,
        s.scheduled_end,
        s.scheduled_hours,
        t.clock_in,
        t.clock_out,
        t.hours_worked as actual_hours,
        coalesce(t.hours_worked, 0) - s.scheduled_hours as hours_variance,
        case
            when t.timecard_id is null then 'no_show'
            when t.hours_worked > s.scheduled_hours + 0.5 then 'over_scheduled'
            when t.hours_worked < s.scheduled_hours - 0.5 then 'under_scheduled'
            else 'on_target'
        end as schedule_adherence_status
    from shifts as s
    left join timecards as t
        on s.employee_id = t.employee_id
        and s.shift_date = t.work_date
        and s.location_id = t.location_id

)

select * from matched
