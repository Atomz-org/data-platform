with

supply_chain as (
    select * from {{ ref('rpt_supply_chain_kpis') }}
)

select
    avg_inventory_turnover as inventory_turnover_ratio,
    overall_avg_lead_time_days as avg_lead_time_days,
    po_on_time_rate as on_time_delivery_pct,
    avg_waste_rate as waste_rate_pct,
    fill_rate,
    delivery_on_time_rate,
    case
        when fill_rate < 0.9 then 'critical'
        when fill_rate < 0.95 then 'warning'
        else 'healthy'
    end as inventory_health,
    case
        when po_on_time_rate > 0.95 then 'excellent'
        when po_on_time_rate > 0.85 then 'good'
        else 'needs_improvement'
    end as delivery_health
from supply_chain
