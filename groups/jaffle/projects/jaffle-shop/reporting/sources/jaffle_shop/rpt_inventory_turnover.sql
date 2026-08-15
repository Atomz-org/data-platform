-- source extract for rpt_inventory_turnover (PII columns excluded by the MDL projection)
select product_id, product_name, location_id, location_name, total_outbound_quantity, outbound_event_count, current_stock, inventory_turnover_ratio, first_outbound_at, last_outbound_at
from main_marts.rpt_inventory_turnover
