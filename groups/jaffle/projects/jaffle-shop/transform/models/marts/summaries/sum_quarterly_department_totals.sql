with 
p as (
    select * from {{ ref('stg_payroll') }}
),

e as (
    select * from {{ ref('dim_employees') }}
),

monthly as (
    select
        {{ sf_date_trunc('month', "p.pay_period_start") }} as payroll_month,
        e.department_id,
        count(distinct p.employee_id) as employee_count,
        sum(p.gross_pay) as total_gross_pay
    from p
    inner join e on p.employee_id = e.employee_id
    group by 1, 2
),
final as (
    select
        {{ sf_date_trunc('quarter', "payroll_month") }} as payroll_quarter,
        department_id,
        round(avg(employee_count), 0) as avg_headcount,
        sum(total_gross_pay) as total_payroll,
        round(sum(total_gross_pay) * 1.0 / nullif(sum(employee_count), 0), 2) as avg_pay_per_employee_month
    from monthly
    group by 1, 2
)
select * from final
