with

employees as (

    select * from {{ ref('dim_employees') }}

),

training as (

    select * from {{ ref('int_training_progress') }}

),

productivity as (

    select
        employee_id,
        avg(orders_per_hour) as avg_orders_per_hour,
        min(work_date) as first_productive_date
    from {{ ref('int_employee_productivity') }}
    where orders_handled > 0
    group by 1

),

lifecycle as (

    select
        e.employee_id,
        e.full_name,
        e.department_name,
        e.hire_date,
        e.termination_date,
        e.is_active,

        -- Stage 1: Hired (always true for all employees)
        true as stage_1_hired,

        -- Stage 2: Training complete (all required courses done)
        case
            when t.required_completion_pct >= 100 then true
            else false
        end as stage_2_training_complete,
        t.required_completion_pct as training_pct,

        -- Stage 3: Fully productive (has handled orders)
        case
            when p.first_productive_date is not null then true
            else false
        end as stage_3_productive,
        p.first_productive_date,
        case
            when p.first_productive_date is not null
            then {{ dbt.datediff('hire_date', 'p.first_productive_date', 'day') }}
        end as days_to_productive,

        -- Stage 4: Performance reviewed
        case
            when t.last_completion_date is not null then true
            else false
        end as stage_4_reviewed,

        -- Attrition indicator
        case
            when termination_date is not null then true
            else false
        end as has_departed,
        tenure_days

    from employees as e
    left join training as t
        on e.employee_id = t.employee_id
    left join productivity as p
        on e.employee_id = p.employee_id

),

summary as (

    select
        {{ dbt.date_trunc('quarter', 'hire_date') }} as hire_quarter,
        department_name,
        count(distinct employee_id) as stage_1_hired_count,
        count(distinct case when stage_2_training_complete then employee_id end) as stage_2_trained_count,
        count(distinct case when stage_3_productive then employee_id end) as stage_3_productive_count,
        count(distinct case when stage_4_reviewed then employee_id end) as stage_4_reviewed_count,
        count(distinct case when has_departed then employee_id end) as departed_count,
        avg(days_to_productive) as avg_days_to_productive,
        round(
            (count(distinct case when stage_2_training_complete then employee_id end) * 100.0
            / nullif(count(distinct employee_id), 0)), 2
        ) as training_completion_rate_pct
    from lifecycle
    group by 1, 2

)

select * from summary
