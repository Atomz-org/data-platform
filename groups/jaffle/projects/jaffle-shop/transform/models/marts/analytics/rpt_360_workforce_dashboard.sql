with

employees as (

    select * from {{ ref('dim_employees') }}

),

emp_performance as (

    select * from {{ ref('scr_employee_performance') }}

),

labor_cost as (

    select
        location_id,
        work_date,
        sum(total_labor_cost) as daily_labor_cost
    from {{ ref('int_labor_cost_daily') }}
    group by 1, 2

),

headcount as (

    select
        location_id,
        count(distinct employee_id) as active_employees,
        avg({{ dbt.datediff('hire_date', dbt.current_timestamp(), 'day') }}) as avg_tenure_days,
        count(case when termination_date is not null then 1 end) as terminated_employees
    from employees
    group by 1

),

performance_summary as (

    select
        count(distinct employee_id) as total_scored,
        avg(performance_score) as avg_performance_score,
        count(case when performance_tier = 'high' then 1 end) as high_performers,
        count(case when performance_tier = 'low' then 1 end) as low_performers
    from emp_performance

),

final as (

    select
        h.location_id,
        h.active_employees,
        h.avg_tenure_days,
        h.terminated_employees,
        case
            when (h.active_employees + h.terminated_employees) > 0
                then round(cast(h.terminated_employees * 100.0 / (h.active_employees + h.terminated_employees) as {{ dbt.type_float() }}), 2)
            else 0
        end as turnover_rate_pct,
        avg(lc.daily_labor_cost) as avg_daily_labor_cost
    from headcount as h
    left join labor_cost as lc
        on h.location_id = lc.location_id
    group by 1, 2, 3, 4

)

select * from final
