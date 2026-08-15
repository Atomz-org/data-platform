with

monthly_payroll as (
    select
        pay_period_start,
        sum(gross_pay) as total_gross,
        sum(net_pay) as total_net,
        count(distinct employee_id) as employee_count
    from {{ ref('fct_payroll') }}
    group by 1
),

compared as (
    select
        pay_period_start,
        total_gross as current_gross,
        lag(total_gross) over (order by pay_period_start) as prior_month_gross,
        total_net as current_net,
        lag(total_net) over (order by pay_period_start) as prior_month_net,
        employee_count as current_employees,
        lag(employee_count) over (order by pay_period_start) as prior_month_employees,
        round(((total_gross - lag(total_gross) over (order by pay_period_start))) * 100.0
            / nullif(lag(total_gross) over (order by pay_period_start), 0), 2) as gross_mom_pct,
        round(total_gross * 1.0 / nullif(employee_count, 0), 2) as avg_pay_per_employee
    from monthly_payroll
)

select * from compared
