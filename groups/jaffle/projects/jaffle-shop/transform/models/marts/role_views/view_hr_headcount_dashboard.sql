with

employees as (

    select * from {{ ref('dim_employees') }}

)

select
    department_id,
    department_name,
    position_title,
    location_id,
    count(*) as total_headcount,
    count(case when is_active = true then 1 end) as active_count,
    count(case when is_active = false then 1 end) as inactive_count,
    round(
        (count(case when is_active = true then 1 end) * 100.0 / nullif(count(*), 0)), 2
    ) as active_pct

from employees
group by department_id, department_name, position_title, location_id
