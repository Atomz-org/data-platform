with

overtime as (
    select
        employee_id,
        {{ dbt.date_trunc('month', 'week_start') }} as month_start,
        sum(total_overtime_hours) as overtime_hours,
        sum(weekly_total_hours) as total_hours,
        sum(weekly_total_hours - total_overtime_hours) as regular_hours
    from {{ ref('int_overtime_hours') }}
    group by 1, 2
),

payroll as (
    select
        employee_id,
        {{ dbt.date_trunc('month', 'pay_period_start') }} as month_start,
        sum(gross_pay) as monthly_gross_pay,
        avg(effective_hourly_rate) as avg_hourly_rate
    from {{ ref('fct_payroll') }}
    group by 1, 2
),

final as (
    select
        o.employee_id,
        o.month_start,
        o.overtime_hours,
        o.regular_hours,
        o.total_hours,
        coalesce(p.avg_hourly_rate, 0) as avg_hourly_rate,
        coalesce(p.avg_hourly_rate * o.overtime_hours * 1.5, 0) as estimated_overtime_cost,
        coalesce(p.monthly_gross_pay, 0) as monthly_gross_pay,
        case
            when coalesce(p.monthly_gross_pay, 0) > 0
            then round(coalesce(p.avg_hourly_rate * o.overtime_hours * 1.5, 0) * 100.0 / p.monthly_gross_pay, 2)
            else null
        end as overtime_cost_pct_of_pay
    from overtime as o
    left join payroll as p
        on o.employee_id = p.employee_id
        and o.month_start = p.month_start
)

select * from final
