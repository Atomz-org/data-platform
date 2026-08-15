with daily_revenue as (
    select
        location_id as location_id,
        revenue_date as work_date,
        total_revenue
    from {{ ref('int_revenue_by_store_daily') }}
),

daily_labor as (
    select
        location_id as location_id,
        work_date,
        sum(total_hours) as total_hours_worked,
        sum(total_labor_cost) as daily_labor_cost,
        sum(employee_count) as employees_working
    from {{ ref('int_labor_cost_daily') }}
    group by location_id, work_date
),

combined as (
    select
        r.location_id,
        r.work_date,
        r.total_revenue,
        coalesce(dl.total_hours_worked, 0) as total_hours_worked,
        coalesce(dl.daily_labor_cost, 0) as daily_labor_cost,
        coalesce(dl.employees_working, 0) as employees_working,
        case
            when coalesce(dl.total_hours_worked, 0) > 0
                then round(
                    (cast(r.total_revenue as {{ dbt.type_float() }})
                    / dl.total_hours_worked), 2
                )
            else null
        end as revenue_per_labor_hour,
        case
            when coalesce(dl.employees_working, 0) > 0
                then round(
                    (cast(r.total_revenue as {{ dbt.type_float() }})
                    / dl.employees_working), 2
                )
            else null
        end as revenue_per_employee
    from daily_revenue as r
    left join daily_labor as dl
        on r.location_id = dl.location_id
        and r.work_date = dl.work_date
)

select
    location_id,
    work_date,
    total_revenue,
    total_hours_worked,
    daily_labor_cost,
    employees_working,
    revenue_per_labor_hour,
    revenue_per_employee,
    avg(revenue_per_labor_hour) over (
        partition by location_id
        order by work_date
        rows between 6 preceding and current row
    ) as revenue_per_hour_7day_avg,
    avg(revenue_per_labor_hour) over (
        partition by location_id
    ) as store_avg_revenue_per_hour
from combined
