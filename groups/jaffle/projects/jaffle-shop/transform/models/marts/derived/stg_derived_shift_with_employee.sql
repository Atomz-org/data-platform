with

shifts as (
    select * from {{ ref('stg_shifts') }}
),

employees as (
    select employee_id, full_name, department_id from {{ ref('stg_employees') }}
),

final as (
    select
        s.shift_id,
        s.employee_id,
        e.full_name,
        e.department_id,
        s.location_id,
        s.shift_date,
        s.scheduled_start,
        s.scheduled_end,
        s.scheduled_hours,
        s.shift_status
    from shifts as s
    left join employees as e on s.employee_id = e.employee_id
)

select * from final
