-- source extract for sc_delivery_route_efficiency (PII columns excluded by the MDL projection)
select supplier_id, supplier_name, total_deliveries, avg_po_total_amount, total_po_total_amount, avg_transit_days, total_goods_value, po_total_amount_pct_of_goods, cost_per_delivery
from main_marts.sc_delivery_route_efficiency
