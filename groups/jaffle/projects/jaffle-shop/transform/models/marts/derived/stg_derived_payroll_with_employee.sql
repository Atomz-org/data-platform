with

payroll as (
    select * from {{ ref('stg_payroll') }}
),

employees as (
    select employee_id, full_name, department_id, location_id from {{ ref('stg_employees') }}
),

final as (
    select
        pr.payroll_id,
        pr.employee_id,
        e.full_name,
        e.department_id,
        e.location_id,
        pr.pay_period_start,
        pr.pay_period_end,
        pr.pay_date,
        pr.gross_pay,
        pr.net_pay,
        pr.gross_pay - pr.net_pay as total_deductions
    from payroll as pr
    left join employees as e on pr.employee_id = e.employee_id
)

select * from final
