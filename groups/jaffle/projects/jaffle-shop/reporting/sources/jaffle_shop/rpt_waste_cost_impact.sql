-- source extract for rpt_waste_cost_impact (PII columns excluded by the MDL projection)
select product_id, product_name, product_type, location_id, location_name, waste_reason, waste_event_count, total_quantity_wasted, total_waste_cost, avg_waste_cost_per_event, first_waste_at, last_waste_at, grand_total_waste_cost, waste_cost_share, waste_cost_rank
from main_marts.rpt_waste_cost_impact
