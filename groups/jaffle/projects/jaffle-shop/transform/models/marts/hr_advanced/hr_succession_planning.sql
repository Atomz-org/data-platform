with

employees as (

    select
        employee_id,
        full_name,
        position_title,
        department_name,
        hire_date,
        is_active,
        {{ dbt.datediff('hire_date', 'current_date', 'month') }} as tenure_months
    from {{ ref('dim_employees') }}
    where is_active = true

),

performance as (

    select
        employee_id,
        performance_score
    from {{ ref('scr_employee_performance') }}

),

final as (

    select
        e.employee_id,
        e.full_name,
        e.position_title,
        e.department_name,
        e.tenure_months,
        coalesce(p.performance_score, 0) as performance_score,
        case
            when e.tenure_months >= 24 and coalesce(p.performance_score, 0) >= 4 then 'ready_now'
            when e.tenure_months >= 12 and coalesce(p.performance_score, 0) >= 3.5 then 'ready_1_year'
            when e.tenure_months >= 6 and coalesce(p.performance_score, 0) >= 3 then 'developing'
            else 'not_ready'
        end as promotion_readiness,
        case
            when coalesce(p.performance_score, 0) >= 4.5 and e.tenure_months >= 18 then 'high_potential'
            when coalesce(p.performance_score, 0) >= 3.5 then 'solid_performer'
            else 'developing_talent'
        end as talent_category
    from employees as e
    left join performance as p on e.employee_id = p.employee_id

)

select * from final
