-- source extract for view_coo_supply_chain_health (PII columns excluded by the MDL projection)
select inventory_turnover_ratio, avg_lead_time_days, on_time_delivery_pct, waste_rate_pct, fill_rate, delivery_on_time_rate, inventory_health, delivery_health
from main_marts.view_coo_supply_chain_health
