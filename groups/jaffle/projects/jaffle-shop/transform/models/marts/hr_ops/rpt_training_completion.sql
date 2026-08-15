with

training_progress as (

    select * from {{ ref('int_training_progress') }}

),

employees as (

    select * from {{ ref('dim_employees') }}

),

employee_training as (

    select
        employees.employee_id,
        employees.full_name,
        employees.department_name,
        employees.position_title,
        employees.location_id,
        employees.tenure_bucket,
        employees.is_active,
        coalesce(training_progress.total_courses_attempted, 0) as total_courses_attempted,
        coalesce(training_progress.total_courses_completed, 0) as total_courses_completed,
        coalesce(training_progress.required_courses_completed, 0) as required_courses_completed,
        coalesce(training_progress.total_required_courses, 0) as total_required_courses,
        coalesce(training_progress.required_completion_pct, 0) as required_completion_pct,
        training_progress.avg_completion_score,
        training_progress.last_completion_date,
        case
            when coalesce(training_progress.required_completion_pct, 0) = 100 then 'fully_compliant'
            when coalesce(training_progress.required_completion_pct, 0) >= 50 then 'partially_compliant'
            else 'non_compliant'
        end as compliance_status

    from employees
    left join training_progress
        on employees.employee_id = training_progress.employee_id
    where employees.is_active

),

department_summary as (

    select
        department_name,
        count(*) as total_employees,
        avg(required_completion_pct) as avg_required_completion_pct,
        count(case when compliance_status = 'fully_compliant' then 1 end) as fully_compliant_count,
        count(case when compliance_status = 'non_compliant' then 1 end) as non_compliant_count,
        avg(avg_completion_score) as avg_score

    from employee_training
    group by department_name

),

final as (

    select
        department_name,
        total_employees,
        round(avg_required_completion_pct, 1) as avg_required_completion_pct,
        fully_compliant_count,
        non_compliant_count,
        round(fully_compliant_count * 100.0 / total_employees, 1) as compliance_rate_pct,
        round(avg_score, 1) as avg_training_score

    from department_summary

)

select * from final
