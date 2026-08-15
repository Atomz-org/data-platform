with

dw as (
    select * from {{ ref('met_daily_waste_metrics') }}
),

dr as (
    select * from {{ ref('met_daily_revenue_by_store') }}
),

daily_waste_rate as (
    select
        dw.waste_date,
        dw.location_id,
        dw.total_waste_cost,
        dr.total_revenue,
        round(dw.total_waste_cost * 100.0 / nullif(dr.total_revenue, 0), 2) as waste_rate_pct
    from dw
    inner join dr
        on dw.waste_date = dr.revenue_date and dw.location_id = dr.location_id
),

alerts as (
    select
        waste_date,
        location_id,
        total_waste_cost,
        total_revenue,
        waste_rate_pct,
        'high_waste_rate' as alert_type,
        case when waste_rate_pct > 5 then 'critical' else 'warning' end as severity
    from daily_waste_rate
    where waste_rate_pct > 3
)

select * from alerts
