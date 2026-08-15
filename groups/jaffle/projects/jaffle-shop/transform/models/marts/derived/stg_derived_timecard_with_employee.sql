with

timecards as (
    select * from {{ ref('stg_timecards') }}
),

employees as (
    select employee_id, full_name, department_id from {{ ref('stg_employees') }}
),

final as (
    select
        tc.timecard_id,
        tc.employee_id,
        e.full_name,
        e.department_id,
        tc.location_id,
        tc.work_date,
        tc.hours_worked,
        tc.break_minutes,
        tc.timecard_status
    from timecards as tc
    left join employees as e on tc.employee_id = e.employee_id
)

select * from final
