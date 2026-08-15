with

employees as (

    select
        employee_id,
        full_name,
        position_title,
        department_name,
        location_id,
        hire_date,
        termination_date,
        is_active
    from {{ ref('dim_employees') }}

),

training as (

    select
        employee_id,
        min(last_completion_date) as first_training_date,
        count(*) as trainings_completed
    from {{ ref('int_training_progress') }}
    group by 1

),

first_shift as (

    select
        employee_id,
        min(shift_date) as first_shift_date
    from {{ ref('fct_shifts') }}
    group by 1

),

reviews as (

    select
        employee_id,
        min(review_date) as first_review_date,
        count(*) as total_reviews,
        avg(overall_score) as avg_review_score
    from {{ ref('stg_performance_reviews') }}
    group by 1

),

final as (

    select
        e.employee_id,
        e.full_name,
        e.position_title,
        e.department_name,
        e.hire_date,
        e.termination_date,
        e.is_active,
        t.first_training_date,
        t.trainings_completed,
        fs.first_shift_date,
        r.first_review_date,
        r.total_reviews,
        r.avg_review_score,
        {{ dbt.datediff('e.hire_date', 'coalesce(fs.first_shift_date, current_date)', 'day') }} as days_hire_to_first_shift,
        {{ dbt.datediff('e.hire_date', 'coalesce(t.first_training_date, current_date)', 'day') }} as days_hire_to_first_training
    from employees as e
    left join training as t on e.employee_id = t.employee_id
    left join first_shift as fs on e.employee_id = fs.employee_id
    left join reviews as r on e.employee_id = r.employee_id

)

select * from final
