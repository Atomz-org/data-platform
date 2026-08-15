with

daily_revenue as (
    select
        revenue_date,
        location_id,
        total_revenue
    from {{ ref('met_daily_revenue_by_store') }}
),

daily_labor as (
    select
        work_date,
        location_id,
        employee_count
    from {{ ref('met_daily_labor_metrics') }}
),

combined as (
    select
        dr.revenue_date as work_date,
        dr.location_id,
        dr.total_revenue,
        dl.employee_count,
        round(dr.total_revenue * 1.0 / nullif(dl.employee_count, 0), 2) as revenue_per_employee
    from daily_revenue as dr
    inner join daily_labor as dl
        on dr.revenue_date = dl.work_date
        and dr.location_id = dl.location_id
),

trended as (
    select
        work_date,
        location_id,
        revenue_per_employee,
        total_revenue,
        employee_count,
        avg(revenue_per_employee) over (
            partition by location_id order by work_date
            rows between 6 preceding and current row
        ) as rpe_7d_ma,
        avg(revenue_per_employee) over (
            partition by location_id order by work_date
            rows between 27 preceding and current row
        ) as rpe_28d_ma,
        case
            when revenue_per_employee > avg(revenue_per_employee) over (
                partition by location_id order by work_date
                rows between 27 preceding and current row
            ) * 1.15 then 'high_productivity'
            when revenue_per_employee < avg(revenue_per_employee) over (
                partition by location_id order by work_date
                rows between 27 preceding and current row
            ) * 0.85 then 'low_productivity'
            else 'normal'
        end as productivity_band
    from combined
)

select * from trended
