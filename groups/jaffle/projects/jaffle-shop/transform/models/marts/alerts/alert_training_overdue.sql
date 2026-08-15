with

e as (
    select * from {{ ref('dim_employees') }}
),

tc as (
    select * from {{ ref('stg_training_completions') }}
),

employee_training as (
    select
        e.employee_id,
        e.full_name,
        e.location_id,
        max(tc.completed_date) as last_training_date,
        {{ sf_datediff('day', "(max(tc.completed_date))", "current_date") }} as days_since_training
    from e
    left join tc on e.employee_id = tc.employee_id
    where e.is_active
    group by 1, 2, 3
),

alerts as (
    select
        employee_id,
        full_name,
        location_id,
        last_training_date,
        days_since_training,
        'training_overdue' as alert_type,
        case
            when days_since_training > 365 or last_training_date is null then 'critical'
            when days_since_training > 180 then 'warning'
            else 'info'
        end as severity
    from employee_training
    where days_since_training > 180 or last_training_date is null
)

select * from alerts
