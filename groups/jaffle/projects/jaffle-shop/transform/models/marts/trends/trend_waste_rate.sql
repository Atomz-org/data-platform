with

daily_waste as (
    select
        waste_date,
        location_id,
        total_waste_cost,
        waste_events
    from {{ ref('met_daily_waste_metrics') }}
),

daily_revenue as (
    select revenue_date, location_id, total_revenue
    from {{ ref('met_daily_revenue_by_store') }}
),

combined as (
    select
        dw.waste_date,
        dw.location_id,
        dw.total_waste_cost,
        dr.total_revenue,
        round(dw.total_waste_cost * 100.0 / nullif(dr.total_revenue, 0), 2) as waste_rate_pct
    from daily_waste as dw
    inner join daily_revenue as dr
        on dw.waste_date = dr.revenue_date
        and dw.location_id = dr.location_id
),

trended as (
    select
        waste_date,
        location_id,
        waste_rate_pct,
        avg(waste_rate_pct) over (
            partition by location_id order by waste_date
            rows between 6 preceding and current row
        ) as waste_rate_7d_ma,
        avg(waste_rate_pct) over (
            partition by location_id order by waste_date
            rows between 27 preceding and current row
        ) as waste_rate_28d_ma,
        case
            when waste_rate_pct > avg(waste_rate_pct) over (
                partition by location_id order by waste_date
                rows between 27 preceding and current row
            ) * 1.5 then 'spike'
            else 'normal'
        end as waste_anomaly_flag
    from combined
)

select * from trended
