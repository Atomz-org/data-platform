with

monthly_payroll as (
    select
        pay_period_start,
        location_id,
        sum(gross_pay) as total_gross_pay,
        sum(net_pay) as total_net_pay,
        count(distinct employee_id) as employee_count
    from {{ ref('fct_payroll') }}
    group by 1, 2
),

trended as (
    select
        pay_period_start,
        location_id,
        total_gross_pay,
        total_net_pay,
        employee_count,
        round(total_gross_pay * 1.0 / nullif(employee_count, 0), 2) as avg_pay_per_employee,
        avg(total_gross_pay) over (
            partition by location_id order by pay_period_start
            rows between 2 preceding and current row
        ) as payroll_3m_ma,
        lag(total_gross_pay) over (partition by location_id order by pay_period_start) as prev_month_payroll,
        round((total_gross_pay - lag(total_gross_pay) over (
            partition by location_id order by pay_period_start
        )) * 100.0 / nullif(lag(total_gross_pay) over (
            partition by location_id order by pay_period_start
        ), 0), 2) as payroll_mom_change_pct
    from monthly_payroll
)

select * from trended
