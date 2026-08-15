with

shifts as (

    select * from {{ ref('stg_shifts') }}

),

timecards as (

    select * from {{ ref('stg_timecards') }}

),

shift_attendance as (

    select
        s.employee_id,
        s.location_id,
        s.shift_date,
        s.scheduled_start,
        t.clock_in,
        case
            when t.timecard_id is null then false
            else true
        end as showed_up,
        case
            when t.clock_in is not null and t.clock_in <= s.scheduled_start
                then true
            else false
        end as on_time
    from shifts as s
    left join timecards as t
        on s.employee_id = t.employee_id
        and s.shift_date = t.work_date
        and s.location_id = t.location_id
    where s.shift_status = 'scheduled'

),

final as (

    select
        employee_id,
        location_id,
        count(*) as total_scheduled_shifts,
        count(case when showed_up then 1 end) as shifts_worked,
        count(case when on_time then 1 end) as shifts_on_time,
        count(case when not showed_up then 1 end) as shifts_missed,
        case
            when count(*) > 0
                then round(cast(count(case when showed_up then 1 end) * 100.0 / count(*) as {{ dbt.type_float() }}), 2)
            else 0
        end as attendance_rate_pct,
        case
            when count(case when showed_up then 1 end) > 0
                then round(cast(count(case when on_time then 1 end) * 100.0 / count(case when showed_up then 1 end) as {{ dbt.type_float() }}), 2)
            else 0
        end as on_time_rate_pct
    from shift_attendance
    group by 1, 2

)

select * from final
