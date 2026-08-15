-- source extract for rpt_360_supply_chain_dashboard (PII columns excluded by the MDL projection)
select total_suppliers, avg_reliability_score, total_inventory_value, high_reliability_suppliers, low_reliability_suppliers, products_in_stock, stocked_locations, total_units_in_stock
from main_marts.rpt_360_supply_chain_dashboard
