with

employees as (

    select * from {{ ref('dim_employees') }}

),

tenure as (

    select * from {{ ref('int_employee_tenure') }}

),

turnover_events as (

    select
        employee_id,
        full_name,
        department_name,
        position_title,
        location_id,
        hire_date,
        termination_date,
        tenure_months,
        tenure_bucket,
        {{ dbt.date_trunc('month', 'hire_date') }} as hire_month,
        {{ dbt.date_trunc('month', 'termination_date') }} as termination_month

    from employees
    -- NOTE: include all employees for complete turnover view
    where termination_date is not null or hire_date is not null

),

monthly_turnover as (

    select
        termination_month as report_month,
        count(*) as terminations,
        avg(tenure_months) as avg_tenure_at_departure_months

    from turnover_events
    group by termination_month

),

tenure_distribution as (

    select
        tenure_bucket,
        count(*) as employee_count,
        count(case when employment_status = 'active' then 1 end) as active_count,
        count(case when termination_date is not null then 1 end) as terminated_count,
        case
            when count(*) > 0
                then round(
                    (count(case when termination_date is not null then 1 end) * 100.0
                    / count(*)), 1
                )
            else 0
        end as turnover_rate_pct

    from employees
    group by tenure_bucket

),

final as (

    select
        tenure_bucket,
        employee_count,
        active_count,
        terminated_count,
        turnover_rate_pct

    from tenure_distribution

)

select * from final
