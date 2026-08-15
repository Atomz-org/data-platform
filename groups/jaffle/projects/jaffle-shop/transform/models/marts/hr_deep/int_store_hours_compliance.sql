with

store_hours as (

    select * from {{ ref('stg_store_hours') }}

),

timecards as (

    select
        location_id,
        work_date,
        min(clock_in) as earliest_clock_in,
        max(clock_out) as latest_clock_out,
        count(distinct employee_id) as employees_on_duty
    from {{ ref('stg_timecards') }}
    where timecard_status = 'approved'
    group by 1, 2

),

final as (

    select
        t.location_id,
        t.work_date,
        sh.day_name,
        sh.open_time as posted_open_time,
        sh.close_time as posted_close_time,
        t.earliest_clock_in,
        t.latest_clock_out,
        t.employees_on_duty,
        sh.is_closed as should_be_closed,
        case
            when sh.is_closed and t.employees_on_duty > 0 then 'open_when_closed'
            when not sh.is_closed and t.employees_on_duty = 0 then 'closed_when_open'
            else 'compliant'
        end as compliance_status
    from timecards as t
    left join store_hours as sh
        on t.location_id = sh.location_id
        and {{ day_of_week_number('t.work_date') }} = sh.day_of_week

)

select * from final
