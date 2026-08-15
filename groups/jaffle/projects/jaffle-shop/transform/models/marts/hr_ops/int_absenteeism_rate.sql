with

shifts as (

    select * from {{ ref('stg_shifts') }}

),

timecards as (

    select * from {{ ref('stg_timecards') }}

),

shift_attendance as (

    select
        shifts.employee_id,
        shifts.location_id,
        shifts.shift_date,
        shifts.shift_id,
        shifts.shift_status,
        case
            when timecards.timecard_id is not null then true
            else false
        end as has_timecard,
        case
            when shifts.shift_status = 'no_show' then true
            when timecards.timecard_id is null then true
            else false
        end as is_absent

    from shifts
    left join timecards
        on shifts.employee_id = timecards.employee_id
        and shifts.location_id = timecards.location_id
        and shifts.shift_date = timecards.work_date

),

employee_absenteeism as (

    select
        employee_id,
        location_id,
        count(*) as total_scheduled_shifts,
        sum(case when is_absent then 1 else 0 end) as absent_shifts,
        sum(case when not is_absent then 1 else 0 end) as attended_shifts,
        case
            when count(*) > 0
                then round(
                    (sum(case when is_absent then 1 else 0 end) * 100.0
                    / count(*)), 1
                )
            else 0
        end as absenteeism_rate_pct,
        min(shift_date) as first_shift_date,
        max(shift_date) as last_shift_date

    from shift_attendance
    group by
        employee_id,
        location_id

)

select * from employee_absenteeism
