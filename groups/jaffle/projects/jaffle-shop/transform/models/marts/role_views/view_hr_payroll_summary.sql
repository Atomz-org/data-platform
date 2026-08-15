with

payroll as (

    select * from {{ ref('fct_payroll') }}

),

monthly_payroll as (

    select
        {{ dbt.date_trunc('month', 'p.pay_period_end') }} as payroll_month,
        p.department_name,
        sum(p.gross_pay) as total_gross_pay,
        sum(p.net_pay) as total_net_pay,
        count(distinct p.employee_id) as employees_paid

    from payroll p
    group by {{ dbt.date_trunc('month', 'p.pay_period_end') }}, p.department_name

)

select
    mp.payroll_month,
    mp.department_name,
    mp.total_gross_pay,
    mp.total_net_pay,
    mp.employees_paid,
    round(mp.total_gross_pay / nullif(mp.employees_paid, 0), 2) as avg_gross_per_employee

from monthly_payroll mp
