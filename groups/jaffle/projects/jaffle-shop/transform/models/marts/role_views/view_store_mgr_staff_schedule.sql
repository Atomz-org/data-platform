with

shifts as (

    select * from {{ ref('fct_shifts') }}

),

employees as (

    select * from {{ ref('dim_employees') }}

)

select
    s.shift_id,
    s.location_id,
    s.employee_id,
    e.full_name,
    e.position_title,
    s.shift_date,
    s.scheduled_start,
    s.scheduled_end,
    s.scheduled_hours,
    s.actual_hours,
    case
        when s.actual_hours is null then 'upcoming'
        when s.actual_hours > s.scheduled_hours then 'overtime'
        when s.actual_hours < s.scheduled_hours then 'short_shift'
        else 'on_schedule'
    end as shift_status

from shifts s
left join employees e on s.employee_id = e.employee_id
