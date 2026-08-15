-- source extract for rpt_waste_analysis (PII columns excluded by the MDL projection)
select product_id, product_name, product_type, waste_reason, event_count, total_quantity_wasted, total_cost_of_waste, avg_quantity_per_event, first_waste_at, last_waste_at, waste_rate, total_inbound_quantity
from main_marts.rpt_waste_analysis
