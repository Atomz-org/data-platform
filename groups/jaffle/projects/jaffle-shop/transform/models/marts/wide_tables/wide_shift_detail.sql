with

shifts as (

    select * from {{ ref('fct_shifts') }}

),

employees as (

    select * from {{ ref('dim_employees') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

)

select
    s.shift_id,
    s.shift_date,
    s.scheduled_start,
    s.actual_end,
    s.scheduled_hours,
    s.actual_hours,
    s.employee_id,
    e.full_name,
    e.position_title,
    e.department_id,
    e.department_name,
    s.location_id,
    l.location_name as store_name,
    round(coalesce(s.actual_hours, s.scheduled_hours) * e.min_hourly_rate, 2) as shift_cost,
    case
        when s.actual_hours > s.scheduled_hours then 'overtime'
        when s.actual_hours < s.scheduled_hours then 'early_out'
        when s.actual_hours is null then 'pending'
        else 'on_schedule'
    end as shift_status

from shifts s
left join employees e on s.employee_id = e.employee_id
left join locations l on s.location_id = l.location_id
