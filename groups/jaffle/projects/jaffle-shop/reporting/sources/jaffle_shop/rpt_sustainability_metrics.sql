-- source extract for rpt_sustainability_metrics (PII columns excluded by the MDL projection)
select waste_month, total_waste_cost, waste_cost_mom_pct, total_waste_quantity, waste_events, total_active_suppliers, supplier_cities, supplier_states
from main_marts.rpt_sustainability_metrics
