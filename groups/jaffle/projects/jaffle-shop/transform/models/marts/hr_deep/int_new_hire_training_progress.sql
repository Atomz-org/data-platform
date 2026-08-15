with

employees as (

    select
        employee_id,
        full_name,
        hire_date,
        location_id
    from {{ ref('dim_employees') }}

),

completions as (

    select * from {{ ref('stg_training_completions') }}

),

new_hires as (

    select
        employee_id,
        full_name,
        hire_date,
        location_id,
        {{ dbt.dateadd('day', 90, 'hire_date') }} as onboarding_end_date
    from employees
    where hire_date is not null

),

training_in_onboarding as (

    select
        nh.employee_id,
        nh.full_name,
        nh.hire_date,
        nh.onboarding_end_date,
        count(tc.training_completion_id) as courses_attempted,
        count(case when tc.completion_status = 'completed' then 1 end) as courses_completed,
        avg(tc.completion_score) as avg_score,
        min(tc.started_date) as first_training_date,
        max(tc.completed_date) as last_completion_date
    from new_hires as nh
    left join completions as tc
        on nh.employee_id = tc.employee_id
        and tc.started_date between nh.hire_date and nh.onboarding_end_date
    group by 1, 2, 3, 4

),

final as (

    select
        *,
        case
            when courses_attempted = 0 then 'not_started'
            when courses_completed >= 5 then 'on_track'
            when courses_completed >= 2 then 'in_progress'
            else 'behind'
        end as onboarding_status
    from training_in_onboarding

)

select * from final
