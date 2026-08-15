with

employees as (

    select
        employee_id,
        hire_date,
        termination_date,
        is_active,
        {{ dbt.date_trunc('month', 'hire_date') }} as hire_month
    from {{ ref('dim_employees') }}

),

cohort_retention as (

    select
        hire_month,
        count(*) as hired_count,
        sum(case
            when is_active
                or {{ dbt.datediff('hire_date', 'coalesce(termination_date, current_date)', 'day') }} >= 30
            then 1 else 0
        end) as retained_30_days,
        sum(case
            when is_active
                or {{ dbt.datediff('hire_date', 'coalesce(termination_date, current_date)', 'day') }} >= 60
            then 1 else 0
        end) as retained_60_days,
        sum(case
            when is_active
                or {{ dbt.datediff('hire_date', 'coalesce(termination_date, current_date)', 'day') }} >= 90
            then 1 else 0
        end) as retained_90_days
    from employees
    group by 1

),

final as (

    select
        hire_month,
        hired_count,
        retained_30_days,
        retained_60_days,
        retained_90_days,
        case when hired_count > 0 then cast(retained_30_days as {{ dbt.type_float() }}) / hired_count * 100 else 0 end as retention_rate_30d,
        case when hired_count > 0 then cast(retained_60_days as {{ dbt.type_float() }}) / hired_count * 100 else 0 end as retention_rate_60d,
        case when hired_count > 0 then cast(retained_90_days as {{ dbt.type_float() }}) / hired_count * 100 else 0 end as retention_rate_90d
    from cohort_retention

)

select * from final
