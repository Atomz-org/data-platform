with

daily_labor as (
    select
        work_date,
        location_id,
        total_labor_cost
    from {{ ref('met_daily_labor_metrics') }}
),

daily_revenue as (
    select
        revenue_date,
        location_id,
        total_revenue
    from {{ ref('met_daily_revenue_by_store') }}
),

combined as (
    select
        dl.work_date,
        dl.location_id,
        dl.total_labor_cost,
        dr.total_revenue,
        round(dl.total_labor_cost * 100.0 / nullif(dr.total_revenue, 0), 2) as labor_cost_pct
    from daily_labor as dl
    inner join daily_revenue as dr
        on dl.work_date = dr.revenue_date
        and dl.location_id = dr.location_id
),

trended as (
    select
        work_date,
        location_id,
        labor_cost_pct,
        avg(labor_cost_pct) over (
            partition by location_id order by work_date
            rows between 6 preceding and current row
        ) as labor_cost_pct_7d_ma,
        avg(labor_cost_pct) over (
            partition by location_id order by work_date
            rows between 27 preceding and current row
        ) as labor_cost_pct_28d_ma,
        case
            when labor_cost_pct > 35 then 'high'
            when labor_cost_pct > 25 then 'moderate'
            else 'efficient'
        end as labor_cost_band
    from combined
)

select * from trended
