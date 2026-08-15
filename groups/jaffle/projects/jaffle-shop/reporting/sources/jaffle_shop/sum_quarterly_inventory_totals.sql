-- source extract for sum_quarterly_inventory_totals (PII columns excluded by the MDL projection)
select metric_quarter, location_id, avg_quarterly_value, quarterly_movement, quarterly_turnover
from main_marts.sum_quarterly_inventory_totals
