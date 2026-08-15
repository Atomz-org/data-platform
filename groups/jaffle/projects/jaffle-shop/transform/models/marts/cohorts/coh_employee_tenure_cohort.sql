with

employees as (

    select * from {{ ref('dim_employees') }}

),

tenure as (

    select * from {{ ref('int_employee_tenure') }}

),

hire_quarter_cohort as (

    select
        e.employee_id,
        e.full_name,
        e.department_name,
        e.position_title,
        e.hire_date,
        e.termination_date,
        e.is_active,
        {{ dbt.date_trunc('quarter', 'e.hire_date') }} as hire_quarter,
        t.tenure_days,
        t.tenure_months,
        t.tenure_bucket
    from employees as e
    inner join tenure as t
        on e.employee_id = t.employee_id

),

cohort_summary as (

    select
        hire_quarter,
        count(distinct employee_id) as cohort_size,
        count(distinct case when is_active then employee_id end) as still_active,
        round(
            (count(distinct case when is_active then employee_id end) * 100.0
            / nullif(count(distinct employee_id), 0)), 2
        ) as retention_rate_pct,
        avg(tenure_days) as avg_tenure_days,
        max(tenure_days) as max_tenure_days,
        count(distinct case when tenure_months < 6 then employee_id end) as left_within_6_months,
        count(distinct department_name) as departments_represented
    from hire_quarter_cohort
    group by 1

)

select * from cohort_summary
