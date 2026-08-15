with

payroll as (

    select
        employee_id,
        pay_period_start,
        gross_pay,
        effective_hourly_rate,
        payroll_hours,
        payroll_overtime_hours,
        deductions
    from {{ ref('fct_payroll') }}

),

timecards as (

    select
        employee_id,
        {{ dbt.date_trunc('month', 'clock_in') }} as work_month,
        sum(hours_worked) as actual_hours
    from {{ ref('fct_timecards') }}
    group by 1, 2

),

expected_vs_actual as (

    select
        p.employee_id,
        {{ dbt.date_trunc('month', 'p.pay_period_start') }} as pay_month,
        sum(p.gross_pay) as total_gross_pay,
        sum(p.payroll_hours + p.payroll_overtime_hours) as expected_hours,
        coalesce(t.actual_hours, 0) as actual_hours,
        sum(p.effective_hourly_rate * (p.payroll_hours + p.payroll_overtime_hours * 1.5)) as expected_pay_from_hours
    from payroll as p
    left join timecards as t
        on p.employee_id = t.employee_id
        and {{ dbt.date_trunc('month', 'p.pay_period_start') }} = t.work_month
    group by 1, 2, t.actual_hours

),

final as (

    select
        employee_id,
        pay_month,
        total_gross_pay,
        expected_pay_from_hours,
        total_gross_pay - expected_pay_from_hours as pay_variance,
        expected_hours,
        actual_hours,
        actual_hours - expected_hours as hours_variance,
        case
            when abs(total_gross_pay - expected_pay_from_hours) / nullif(expected_pay_from_hours, 0) > 0.10
            then 'significant_variance'
            when abs(total_gross_pay - expected_pay_from_hours) / nullif(expected_pay_from_hours, 0) > 0.03
            then 'minor_variance'
            else 'within_tolerance'
        end as variance_status
    from expected_vs_actual

)

select * from final
