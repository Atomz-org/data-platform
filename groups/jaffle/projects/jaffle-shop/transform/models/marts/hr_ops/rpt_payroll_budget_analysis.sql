with

payroll_trend as (

    select * from {{ ref('int_payroll_cost_trend') }}

),

quarterly_summary as (

    select
        department_id,
        department_name,
        {{ dbt.date_trunc('quarter', 'pay_month') }} as pay_quarter,
        sum(total_gross_pay) as quarterly_gross_pay,
        sum(total_net_pay) as quarterly_net_pay,
        sum(total_deductions) as quarterly_deductions,
        sum(total_hours) as quarterly_hours,
        sum(total_overtime_hours) as quarterly_overtime_hours,
        avg(employee_count) as avg_headcount,
        avg(avg_cost_per_hour) as avg_cost_per_hour

    from payroll_trend
    group by
        department_id,
        department_name,
        {{ dbt.date_trunc('quarter', 'pay_month') }}

),

monthly_detail as (

    select
        department_id,
        department_name,
        pay_month,
        employee_count,
        total_gross_pay,
        total_net_pay,
        total_deductions,
        total_hours,
        total_overtime_hours,
        avg_cost_per_hour,
        avg_gross_pay_per_employee,
        prev_month_gross_pay,
        month_over_month_change_pct,
        avg(total_gross_pay) over (
            partition by department_id
            order by pay_month
            rows between 2 preceding and current row
        ) as rolling_3mo_avg_gross_pay,
        case
            when total_hours > 0
                then round(total_overtime_hours * 100.0 / total_hours, 1)
            else 0
        end as overtime_pct_of_total

    from payroll_trend

)

select * from monthly_detail
