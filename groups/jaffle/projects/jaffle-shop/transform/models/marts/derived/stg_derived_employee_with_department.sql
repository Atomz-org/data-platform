with

employees as (
    select * from {{ ref('stg_employees') }}
),

departments as (
    select department_id, department_name from {{ ref('stg_departments') }}
),

final as (
    select
        e.employee_id,
        e.full_name,
        e.department_id,
        d.department_name,
        e.location_id,
        e.hire_date,
        e.employment_status
    from employees as e
    left join departments as d on e.department_id = d.department_id
)

select * from final
