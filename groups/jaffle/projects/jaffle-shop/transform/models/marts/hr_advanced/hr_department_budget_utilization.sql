with

payroll as (
    select * from {{ ref('fct_payroll') }}
),

employees as (
    select * from {{ ref('dim_employees') }}
),

dept_payroll as (
    select
        e.department_name,
        {{ dbt.date_trunc('month', 'p.pay_period_start') }} as pay_month,
        sum(p.gross_pay) as total_labor_spend,
        count(distinct p.employee_id) as employee_count
    from payroll as p
    inner join employees as e
        on p.employee_id = e.employee_id
    group by 1, 2
),

dept_avg as (
    select
        department_name,
        avg(total_labor_spend) as avg_monthly_spend
    from dept_payroll
    group by 1
),

final as (
    select
        dp.department_name,
        dp.pay_month,
        dp.total_labor_spend,
        dp.employee_count,
        da.avg_monthly_spend as monthly_budget_allocation,
        dp.total_labor_spend - da.avg_monthly_spend as budget_variance,
        case
            when da.avg_monthly_spend > 0
            then dp.total_labor_spend / da.avg_monthly_spend * 100
            else null
        end as budget_utilization_pct,
        sum(dp.total_labor_spend) over (
            partition by dp.department_name order by dp.pay_month
        ) as ytd_labor_spend
    from dept_payroll as dp
    inner join dept_avg as da on dp.department_name = da.department_name
)

select * from final
