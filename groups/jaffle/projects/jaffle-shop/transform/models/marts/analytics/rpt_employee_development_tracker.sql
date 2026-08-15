with

employees as (

    select * from {{ ref('dim_employees') }}

),

training_progress as (

    select * from {{ ref('int_training_progress') }}

),

performance as (

    select
        employee_id,
        avg(overall_score) as avg_performance_score,
        count(review_id) as review_count,
        max(review_date) as latest_review_date
    from {{ ref('stg_performance_reviews') }}
    group by 1

),

final as (

    select
        e.employee_id,
        e.full_name,
        e.hire_date,
        {{ dbt.datediff('e.hire_date', dbt.current_timestamp(), 'day') }} as tenure_days,
        tp.total_required_courses,
        tp.required_courses_completed,
        tp.required_completion_pct,
        case when tp.required_completion_pct = 100 then 'fully_compliant' when tp.required_completion_pct >= 50 then 'partially_compliant' else 'non_compliant' end as completion_status,
        p.avg_performance_score,
        p.review_count,
        p.latest_review_date,
        case
            when {{ dbt.datediff('e.hire_date', dbt.current_timestamp(), 'day') }} <= 90 then 'onboarding'
            when {{ dbt.datediff('e.hire_date', dbt.current_timestamp(), 'day') }} <= 365 then 'first_year'
            when {{ dbt.datediff('e.hire_date', dbt.current_timestamp(), 'day') }} <= 730 then 'developing'
            else 'experienced'
        end as career_stage
    from employees as e
    left join training_progress as tp
        on e.employee_id = tp.employee_id
    left join performance as p
        on e.employee_id = p.employee_id

)

select * from final
