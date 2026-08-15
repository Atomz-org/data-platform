with

employees as (

    select * from {{ ref('stg_employees') }}

),

tenure_calc as (

    select
        employee_id,
        hire_date,
        termination_date,
        employment_status,
        {{ dbt.datediff('hire_date', "coalesce(termination_date, current_date)", 'day') }} as tenure_days,
        {{ dbt.datediff('hire_date', "coalesce(termination_date, current_date)", 'month') }} as tenure_months,
        case
            when {{ dbt.datediff('hire_date', "coalesce(termination_date, current_date)", 'month') }} < 6
                then 'under_6_months'
            when {{ dbt.datediff('hire_date', "coalesce(termination_date, current_date)", 'month') }} < 12
                then '6_to_12_months'
            when {{ dbt.datediff('hire_date', "coalesce(termination_date, current_date)", 'month') }} < 24
                then '1_to_2_years'
            when {{ dbt.datediff('hire_date', "coalesce(termination_date, current_date)", 'month') }} < 60
                then '2_to_5_years'
            else '5_plus_years'
        end as tenure_bucket

    from employees

)

select * from tenure_calc
