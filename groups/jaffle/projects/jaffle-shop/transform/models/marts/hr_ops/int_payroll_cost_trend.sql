with

payroll as (

    select * from {{ ref('stg_payroll') }}

),

employees as (

    select * from {{ ref('stg_employees') }}

),

departments as (

    select * from {{ ref('stg_departments') }}

),

payroll_enriched as (

    select
        payroll.payroll_id,
        payroll.employee_id,
        employees.department_id,
        departments.department_name,
        employees.position_id,
        {{ dbt.date_trunc('month', 'payroll.pay_date') }} as pay_month,
        payroll.payroll_hours,
        payroll.payroll_overtime_hours,
        payroll.gross_pay,
        payroll.deductions,
        payroll.net_pay

    from payroll
    inner join employees
        on payroll.employee_id = employees.employee_id
    inner join departments
        on employees.department_id = departments.department_id

),

monthly_trend as (

    select
        department_id,
        department_name,
        pay_month,
        count(distinct employee_id) as employee_count,
        sum(payroll_hours) as total_hours,
        sum(payroll_overtime_hours) as total_overtime_hours,
        sum(gross_pay) as total_gross_pay,
        sum(deductions) as total_deductions,
        sum(net_pay) as total_net_pay,
        case
            when sum(payroll_hours) > 0
                then round(sum(gross_pay) / sum(payroll_hours), 2)
            else null
        end as avg_cost_per_hour,
        round(sum(gross_pay) / nullif(count(distinct employee_id), 0), 2) as avg_gross_pay_per_employee

    from payroll_enriched
    group by
        department_id,
        department_name,
        pay_month

),

with_lag as (

    select
        department_id,
        department_name,
        pay_month,
        employee_count,
        total_hours,
        total_overtime_hours,
        total_gross_pay,
        total_deductions,
        total_net_pay,
        avg_cost_per_hour,
        avg_gross_pay_per_employee,
        lag(total_gross_pay) over (
            partition by department_id
            order by pay_month
        ) as prev_month_gross_pay,
        case
            when lag(total_gross_pay) over (
                partition by department_id
                order by pay_month
            ) > 0
                then round(
                    ((total_gross_pay - lag(total_gross_pay) over (
                        partition by department_id
                        order by pay_month
                    )) * 100.0
                    / lag(total_gross_pay) over (
                        partition by department_id
                        order by pay_month
                    )), 1
                )
            else null
        end as month_over_month_change_pct

    from monthly_trend

)

select * from with_lag
