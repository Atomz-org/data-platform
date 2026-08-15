-- source extract for rpt_supplier_spend_trend (PII columns excluded by the MDL projection)
select supplier_id, supplier_name, order_month, count_purchase_orders, total_spend, avg_unit_cost, total_quantity_ordered, prev_month_spend, same_month_last_year_spend, mom_spend_change, yoy_spend_change, cumulative_spend
from main_marts.rpt_supplier_spend_trend
