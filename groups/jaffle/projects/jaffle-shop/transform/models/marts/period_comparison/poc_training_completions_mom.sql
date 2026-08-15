with

monthly_training as (
    select
        {{ sf_date_trunc('month', "completed_date") }} as completion_month,
        count(*) as completions,
        count(distinct employee_id) as unique_employees,
        count(distinct training_course_id) as unique_courses
    from {{ ref('stg_training_completions') }}
    group by 1
),

compared as (
    select
        completion_month,
        completions as current_completions,
        lag(completions) over (order by completion_month) as prior_month_completions,
        unique_employees as current_employees,
        lag(unique_employees) over (order by completion_month) as prior_month_employees,
        round(((completions - lag(completions) over (order by completion_month))) * 100.0
            / nullif(lag(completions) over (order by completion_month), 0), 2) as completions_mom_pct
    from monthly_training
)

select * from compared
