with

payroll as (

    select * from {{ ref('fct_payroll') }}

),

latest_period as (

    select max(pay_period_end) as max_period from payroll

)

select
    p.payroll_id,
    p.employee_id,
    p.department_name,
    p.pay_period_start,
    p.pay_period_end,
    p.payroll_hours,
    p.payroll_overtime_hours,
    p.gross_pay,
    p.deductions,
    p.net_pay,
    current_timestamp as exported_at,
    'recce_dw' as source_system

from payroll p
inner join latest_period lp on p.pay_period_end = lp.max_period
