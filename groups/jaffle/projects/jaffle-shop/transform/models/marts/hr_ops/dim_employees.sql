with

employees as (

    select * from {{ ref('int_employee_enriched') }}

),

tenure as (

    select * from {{ ref('int_employee_tenure') }}

),

final as (

    select
        employees.employee_id,
        employees.first_name,
        employees.last_name,
        employees.full_name,
        employees.email,
        employees.employment_status,
        employees.hire_date,
        employees.termination_date,
        employees.location_id,
        employees.department_id,
        employees.department_name,
        employees.position_id,
        employees.position_title,
        employees.pay_grade,
        employees.min_hourly_rate,
        employees.max_hourly_rate,
        employees.is_management,
        tenure.tenure_days,
        tenure.tenure_months,
        tenure.tenure_bucket,
        case
            when employees.employment_status = 'active' then true
            else false
        end as is_active

    from employees
    left join tenure
        on employees.employee_id = tenure.employee_id

)

select * from final
