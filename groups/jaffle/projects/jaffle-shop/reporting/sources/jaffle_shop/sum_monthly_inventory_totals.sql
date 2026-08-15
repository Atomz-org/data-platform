-- source extract for sum_monthly_inventory_totals (PII columns excluded by the MDL projection)
select month_start, location_id, total_units_on_hand, monthly_movements, turnover_ratio, prior_month_value
from main_marts.sum_monthly_inventory_totals
