-- source extract for kpi_inventory_turnover_ratio (PII columns excluded by the MDL projection)
select month_start, location_id, total_units_on_hand, monthly_movements, turnover_ratio, turnover_band
from main_marts.kpi_inventory_turnover_ratio
