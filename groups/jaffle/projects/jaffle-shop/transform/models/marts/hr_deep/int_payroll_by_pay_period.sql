with

payroll as (

    select * from {{ ref('stg_payroll') }}

),

final as (

    select
        pay_period_start,
        pay_period_end,
        pay_date,
        count(distinct employee_id) as employee_count,
        sum(payroll_hours) as total_hours,
        sum(payroll_overtime_hours) as total_overtime_hours,
        sum(gross_pay) as total_gross_pay,
        sum(deductions) as total_deductions,
        sum(net_pay) as total_net_pay,
        avg(gross_pay) as avg_gross_pay_per_employee,
        avg(deductions) as avg_deductions_per_employee,
        case
            when sum(gross_pay) > 0
                then round(cast(sum(deductions) * 100.0 / sum(gross_pay) as {{ dbt.type_float() }}), 2)
            else 0
        end as deduction_rate_pct,
        case
            when sum(payroll_hours) > 0
                then round(cast(sum(payroll_overtime_hours) * 100.0 / sum(payroll_hours) as {{ dbt.type_float() }}), 2)
            else 0
        end as overtime_pct
    from payroll
    group by 1, 2, 3

)

select * from final
