with 
p as (
    select * from {{ ref('stg_payroll') }}
),

e as (
    select * from {{ ref('dim_employees') }}
),

final as (
    select
        {{ sf_date_trunc('month', "p.pay_period_start") }} as payroll_month,
        e.department_id,
        count(distinct p.employee_id) as employee_count,
        sum(p.gross_pay) as total_gross_pay,
        sum(p.net_pay) as total_net_pay,
        round(sum(p.gross_pay) * 1.0 / nullif(count(distinct p.employee_id), 0), 2) as avg_pay_per_employee
    from p
    inner join e on p.employee_id = e.employee_id
    group by 1, 2
)
select * from final
