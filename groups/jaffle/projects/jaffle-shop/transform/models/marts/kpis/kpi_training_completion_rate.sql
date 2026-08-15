with employees as (
    select count(distinct employee_id) as total_employees
    from {{ ref('dim_employees') }}
    where is_active
),
trained as (
    select
        {{ sf_date_trunc('month', "completed_date") }} as completion_month,
        count(distinct employee_id) as trained_employees,
        count(*) as total_completions
    from {{ ref('stg_training_completions') }}
    group by 1
),
final as (
    select
        t.completion_month,
        t.trained_employees,
        t.total_completions,
        e.total_employees,
        round(t.trained_employees * 100.0 / nullif(e.total_employees, 0), 2) as completion_rate_pct
    from trained as t
    cross join employees as e
)
select * from final
