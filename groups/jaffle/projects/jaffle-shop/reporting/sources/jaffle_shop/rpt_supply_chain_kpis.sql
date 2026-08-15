-- source extract for rpt_supply_chain_kpis (PII columns excluded by the MDL projection)
select avg_inventory_turnover, products_in_stock, total_product_locations, overall_avg_lead_time_days, po_on_time_rate, avg_waste_rate, total_waste_cost, total_waste_quantity, fill_rate, items_above_reorder_point, total_tracked_items, delivery_on_time_rate, total_deliveries, total_on_time_deliveries
from main_marts.rpt_supply_chain_kpis
