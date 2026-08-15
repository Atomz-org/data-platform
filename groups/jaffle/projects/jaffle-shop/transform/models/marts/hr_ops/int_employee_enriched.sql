with

employees as (

    select * from {{ ref('stg_employees') }}

),

departments as (

    select * from {{ ref('stg_departments') }}

),

positions as (

    select * from {{ ref('stg_positions') }}

),

enriched as (

    select

        employees.employee_id,
        employees.location_id,
        employees.first_name,
        employees.last_name,
        employees.full_name,
        employees.email,
        employees.employment_status,
        employees.hire_date,
        employees.termination_date,

        departments.department_id,
        departments.department_name,

        positions.position_id,
        positions.position_title,
        positions.pay_grade,
        positions.min_hourly_rate,
        positions.max_hourly_rate,
        positions.is_management

    from employees
    left join departments
        on employees.department_id = departments.department_id
    left join positions
        on employees.position_id = positions.position_id

)

select * from enriched
