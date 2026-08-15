with

payroll as (

    select * from {{ ref('stg_payroll') }}

),

employees as (

    select * from {{ ref('int_employee_enriched') }}

),

final as (

    select
        payroll.payroll_id,
        payroll.employee_id,
        employees.full_name as full_name,
        employees.department_name,
        employees.position_title,
        employees.location_id,
        payroll.pay_period_start,
        payroll.pay_period_end,
        payroll.pay_date,
        payroll.payroll_hours,
        payroll.payroll_overtime_hours,
        payroll.gross_pay,
        payroll.deductions,
        payroll.net_pay,
        case
            when payroll.payroll_hours > 0
                then round(payroll.gross_pay / payroll.payroll_hours, 2)
            else null
        end as effective_hourly_rate,
        case
            when payroll.gross_pay > 0
                then round(payroll.deductions / payroll.gross_pay * 100, 1)
            else null
        end as deduction_pct

    from payroll
    left join employees
        on payroll.employee_id = employees.employee_id

)

select * from final
