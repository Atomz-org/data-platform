with

employees as (

    select
        employee_id,
        full_name,
        department_name,
        hire_date,
        is_active,
        {{ dbt.datediff('hire_date', 'current_date', 'month') }} as tenure_months
    from {{ ref('dim_employees') }}
    where is_active = true

),

absenteeism as (

    select
        employee_id,
        absent_shifts
    from {{ ref('int_absenteeism_rate') }}

),

overtime as (

    select
        employee_id,
        sum(total_overtime_hours) as total_total_overtime_hours,
        avg(total_overtime_hours) as avg_monthly_overtime
    from {{ ref('int_overtime_hours') }}
    group by 1

),

final as (

    select
        e.employee_id,
        e.full_name,
        e.department_name,
        e.tenure_months,
        coalesce(ab.absent_shifts, 0) as absent_shifts,
        coalesce(ot.avg_monthly_overtime, 0) as avg_monthly_overtime,
        -- Engagement proxy: low absence + moderate overtime + long tenure = engaged
        {{ sf_least(["100", "((case when coalesce(ab.absent_shifts, 0) < 3 then 40 when coalesce(ab.absent_shifts, 0) < 5 then 25 else 10 end) + (case when e.tenure_months > 24 then 30 when e.tenure_months > 12 then 20 else 10 end) + (case when coalesce(ot.avg_monthly_overtime, 0) between 1 and 10 then 30 when coalesce(ot.avg_monthly_overtime, 0) > 0 then 15 else 10 end))"]) }} as engagement_score,
        case
            when coalesce(ab.absent_shifts, 0) < 3 and e.tenure_months > 12 then 'engaged'
            when coalesce(ab.absent_shifts, 0) > 8 then 'disengaged'
            else 'neutral'
        end as engagement_category
    from employees as e
    left join absenteeism as ab on e.employee_id = ab.employee_id
    left join overtime as ot on e.employee_id = ot.employee_id

)

select * from final
