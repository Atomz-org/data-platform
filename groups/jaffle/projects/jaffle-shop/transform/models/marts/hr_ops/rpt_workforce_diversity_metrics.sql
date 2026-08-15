with

employees as (

    select * from {{ ref('dim_employees') }}

),

by_department_and_level as (

    select
        department_name,
        position_title,
        pay_grade,
        count(*) as total_employees,
        sum(case when is_active then 1 else 0 end) as active_employees,
        sum(case when not is_active then 1 else 0 end) as inactive_employees,
        round(avg(tenure_days), 0) as avg_tenure_days,
        round(avg(tenure_months), 0) as avg_tenure_months

    from employees
    group by
        department_name,
        position_title,
        pay_grade

),

department_totals as (

    select
        department_name,
        sum(total_employees) as dept_total,
        sum(active_employees) as dept_active_total

    from by_department_and_level
    group by department_name

),

overall_totals as (

    select
        count(*) as org_total,
        sum(case when is_active then 1 else 0 end) as org_active_total

    from employees

),

final as (

    select
        by_department_and_level.department_name,
        by_department_and_level.position_title,
        by_department_and_level.pay_grade,
        by_department_and_level.total_employees,
        by_department_and_level.active_employees,
        by_department_and_level.inactive_employees,
        by_department_and_level.avg_tenure_days,
        by_department_and_level.avg_tenure_months,
        case
            when department_totals.dept_total > 0
                then round(
                    (by_department_and_level.total_employees * 100.0
                    / department_totals.dept_total), 1
                )
            else 0
        end as pct_of_department,
        case
            when overall_totals.org_total > 0
                then round(
                    (by_department_and_level.total_employees * 100.0
                    / overall_totals.org_total), 1
                )
            else 0
        end as pct_of_organization,
        department_totals.dept_total as department_headcount,
        overall_totals.org_total as organization_headcount

    from by_department_and_level
    inner join department_totals
        on by_department_and_level.department_name = department_totals.department_name
    cross join overall_totals

)

select * from final
