-- source extract for sc_supplier_price_comparison (PII columns excluded by the MDL projection)
select product_id, supplier_id, supplier_name, purchase_count, avg_unit_cost, min_unit_cost, max_unit_cost, total_quantity, lowest_avg_cost, cost_premium, cost_premium_pct, price_position
from main_marts.sc_supplier_price_comparison
