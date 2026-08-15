with

employees as (

    select * from {{ ref('dim_employees') }}

),

-- Generate month boundaries from employee hire dates
months as (

    select distinct
        {{ dbt.date_trunc('month', 'hire_date') }} as month_start

    from employees

),

-- For each month, count active employees per location
monthly_roster as (

    select
        m.month_start,
        e.location_id,
        count(e.employee_id) as headcount,
        sum(case when e.is_management then 1 else 0 end) as management_count,
        sum(case when not e.is_management then 1 else 0 end) as non_management_count,
        count(
            case
                when e.hire_date >= m.month_start
                    and e.hire_date < m.month_start + interval '1 month'
                then e.employee_id
            end
        ) as new_hires_in_month,
        count(
            case
                when e.termination_date >= m.month_start
                    and e.termination_date < m.month_start + interval '1 month'
                then e.employee_id
            end
        ) as terminations_in_month

    from months as m

    inner join employees as e
        on e.hire_date <= m.month_start + interval '1 month' - interval '1 day'
        and (
            e.termination_date is null
            or e.termination_date >= m.month_start
        )

    group by 1, 2

)

select * from monthly_roster
