with

employees as (
    select * from {{ ref('stg_employees') }}
),

positions as (
    select position_id, position_title, pay_grade from {{ ref('stg_positions') }}
),

final as (
    select
        e.employee_id,
        e.full_name,
        e.position_id,
        p.position_title,
        p.pay_grade,
        e.department_id,
        e.location_id,
        e.hire_date,
        e.employment_status
    from employees as e
    left join positions as p on e.position_id = p.position_id
)

select * from final
