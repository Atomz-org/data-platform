with

employees as (

    select
        employee_id,
        full_name,
        position_title,
        department_name,
        hire_date,
        is_active
    from {{ ref('dim_employees') }}

),

positions as (

    select
        position_id,
        position_title,
        min_hourly_rate,
        max_hourly_rate
    from {{ ref('stg_positions') }}

),

payroll as (

    select
        employee_id,
        avg(gross_pay) as avg_monthly_pay,
        avg(effective_hourly_rate) as avg_hourly_rate
    from {{ ref('fct_payroll') }}
    group by 1

),

final as (

    select
        e.employee_id,
        e.full_name,
        e.position_title,
        e.department_name,
        e.is_active,
        pr.avg_monthly_pay,
        pr.avg_hourly_rate,
        p.min_hourly_rate,
        p.max_hourly_rate,
        case
            when p.max_hourly_rate > p.min_hourly_rate
            then (pr.avg_monthly_pay * 12 - p.min_hourly_rate) / (p.max_hourly_rate - p.min_hourly_rate) * 100
            else null
        end as salary_range_penetration_pct,
        avg(pr.avg_monthly_pay) over (partition by e.department_name) as dept_avg_monthly_pay,
        pr.avg_monthly_pay - avg(pr.avg_monthly_pay) over (partition by e.department_name) as pay_vs_dept_avg
    from employees as e
    left join payroll as pr on e.employee_id = pr.employee_id
    left join positions as p on e.position_title = p.position_title

)

select * from final
