with final as (
    select
        pay_period_start,
        count(distinct employee_id) as employee_count,
        sum(gross_pay) as total_gross_pay,
        sum(net_pay) as total_net_pay,
        sum(gross_pay) - sum(net_pay) as total_deductions,
        round(sum(gross_pay) * 1.0 / nullif(count(distinct employee_id), 0), 2) as avg_gross_per_employee,
        lag(sum(gross_pay)) over (order by pay_period_start) as prior_period_gross
    from {{ ref('fct_payroll') }}
    group by 1
)
select * from final
