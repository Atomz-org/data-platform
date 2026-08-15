with

timecards as (

    select * from {{ ref('stg_timecards') }}

),

employees as (

    select * from {{ ref('int_employee_enriched') }}

),

final as (

    select
        timecards.timecard_id,
        timecards.employee_id,
        timecards.location_id,
        employees.full_name as full_name,
        employees.department_name,
        employees.position_title,
        timecards.work_date,
        timecards.clock_in,
        timecards.clock_out,
        timecards.hours_worked,
        timecards.break_minutes,
        timecards.timecard_status,
        round(timecards.hours_worked - (timecards.break_minutes / 60.0), 2) as net_hours_worked,
        case
            when timecards.hours_worked > 8 then timecards.hours_worked - 8
            else 0
        end as overtime_hours

    from timecards
    left join employees
        on timecards.employee_id = employees.employee_id

)

select * from final
