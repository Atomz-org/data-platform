with

employees as (

    select * from {{ ref('dim_employees') }}

),

departments as (

    select * from {{ ref('dim_departments') }}

),

current_headcount as (

    select
        department_name,
        count(*) as total_employees,
        sum(case when is_active then 1 else 0 end) as active_employees,
        sum(case when not is_active then 1 else 0 end) as inactive_employees,
        sum(case when is_active and tenure_bucket = 'under_6_months' then 1 else 0 end) as new_hires,
        sum(case when is_active and tenure_bucket = '5_plus_years' then 1 else 0 end) as long_tenured,
        round(avg(case when is_active then tenure_days end), 0) as avg_active_tenure_days,
        round(avg(case when is_active then tenure_months end), 0) as avg_active_tenure_months

    from employees
    group by department_name

),

monthly_hires as (

    select
        department_name,
        {{ dbt.date_trunc('month', 'hire_date') }} as hire_month,
        count(*) as hires_in_month

    from employees
    group by
        department_name,
        {{ dbt.date_trunc('month', 'hire_date') }}

),

monthly_terminations as (

    select
        department_name,
        {{ dbt.date_trunc('month', 'termination_date') }} as termination_month,
        count(*) as terminations_in_month

    from employees
    where termination_date is not null
    group by
        department_name,
        {{ dbt.date_trunc('month', 'termination_date') }}

),

headcount_trend as (

    select
        coalesce(monthly_hires.department_name, monthly_terminations.department_name) as department_name,
        coalesce(monthly_hires.hire_month, monthly_terminations.termination_month) as trend_month,
        coalesce(monthly_hires.hires_in_month, 0) as hires,
        coalesce(monthly_terminations.terminations_in_month, 0) as terminations,
        coalesce(monthly_hires.hires_in_month, 0)
            - coalesce(monthly_terminations.terminations_in_month, 0) as net_change

    from monthly_hires
    full outer join monthly_terminations
        on monthly_hires.department_name = monthly_terminations.department_name
        and monthly_hires.hire_month = monthly_terminations.termination_month

),

final as (

    select
        current_headcount.department_name,
        current_headcount.total_employees,
        current_headcount.active_employees,
        current_headcount.inactive_employees,
        current_headcount.new_hires,
        current_headcount.long_tenured,
        current_headcount.avg_active_tenure_days,
        current_headcount.avg_active_tenure_months,
        case
            when current_headcount.active_employees > 0
                then round(
                    (current_headcount.new_hires * 100.0
                    / current_headcount.active_employees), 1
                )
            else 0
        end as new_hire_pct,
        case
            when current_headcount.total_employees > 0
                then round(
                    (current_headcount.inactive_employees * 100.0
                    / current_headcount.total_employees), 1
                )
            else 0
        end as attrition_rate_pct

    from current_headcount

)

select * from final
