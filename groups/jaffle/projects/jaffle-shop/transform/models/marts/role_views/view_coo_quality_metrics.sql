with

waste_analysis as (
    select * from {{ ref('rpt_waste_analysis') }}
),

waste_summary as (
    select
        sum(event_count) as total_waste_events,
        sum(total_cost_of_waste) as total_waste_cost,
        avg(total_cost_of_waste) as avg_waste_cost_per_product,
        count(distinct product_id) as products_with_waste
    from waste_analysis
),

supplier_scorecard as (
    select
        count(*) as total_suppliers,
        avg(fulfillment_rate) as avg_fulfillment_rate,
        count(case when fulfillment_rate < 0.7 then 1 end) as low_quality_suppliers
    from {{ ref('rpt_supplier_scorecard') }}
)

select
    ws.total_waste_events,
    ws.total_waste_cost,
    ws.avg_waste_cost_per_product,
    ws.products_with_waste,
    ss.total_suppliers,
    ss.avg_fulfillment_rate as avg_supplier_quality,
    ss.low_quality_suppliers,
    case
        when ws.total_waste_events > 100 then 'high_waste'
        when ws.total_waste_events > 50 then 'moderate_waste'
        else 'low_waste'
    end as waste_severity
from waste_summary as ws
cross join supplier_scorecard as ss
