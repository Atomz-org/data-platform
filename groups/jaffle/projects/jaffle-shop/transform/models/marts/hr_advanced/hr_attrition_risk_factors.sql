with

employees as (

    select
        employee_id,
        full_name,
        department_name,
        position_title,
        hire_date,
        termination_date,
        is_active,
        {{ dbt.datediff('hire_date', 'coalesce(termination_date, current_date)', 'month') }} as tenure_months
    from {{ ref('dim_employees') }}

),

performance as (

    select
        employee_id,
        performance_score
    from {{ ref('scr_employee_performance') }}

),

overtime as (

    select
        employee_id,
        avg(total_overtime_hours) as avg_monthly_overtime
    from {{ ref('int_overtime_hours') }}
    group by 1

),

final as (

    select
        e.employee_id,
        e.full_name,
        e.department_name,
        e.position_title,
        e.tenure_months,
        e.is_active,
        e.termination_date,
        coalesce(p.performance_score, 0) as performance_score,
        coalesce(ot.avg_monthly_overtime, 0) as avg_monthly_overtime,
        -- Risk factors
        case when e.tenure_months < 6 then 1 else 0 end as short_tenure_risk,
        case when coalesce(ot.avg_monthly_overtime, 0) > 20 then 1 else 0 end as high_overtime_risk,
        case when coalesce(p.performance_score, 0) < 2.5 then 1 else 0 end as low_performance_risk,
        -- Composite attrition risk
        (case when e.tenure_months < 6 then 1 else 0 end)
        + (case when coalesce(ot.avg_monthly_overtime, 0) > 20 then 1 else 0 end)
        + (case when coalesce(p.performance_score, 0) < 2.5 then 1 else 0 end) as risk_factor_count,
        case
            when (case when e.tenure_months < 6 then 1 else 0 end)
                + (case when coalesce(ot.avg_monthly_overtime, 0) > 20 then 1 else 0 end)
                + (case when coalesce(p.performance_score, 0) < 2.5 then 1 else 0 end) >= 2
            then 'high_risk'
            when (case when e.tenure_months < 6 then 1 else 0 end)
                + (case when coalesce(ot.avg_monthly_overtime, 0) > 20 then 1 else 0 end)
                + (case when coalesce(p.performance_score, 0) < 2.5 then 1 else 0 end) = 1
            then 'moderate_risk'
            else 'low_risk'
        end as attrition_risk_level
    from employees as e
    left join performance as p on e.employee_id = p.employee_id
    left join overtime as ot on e.employee_id = ot.employee_id

)

select * from final
