-- source extract for rpt_purchase_order_summary (PII columns excluded by the MDL projection)
select order_month, total_orders, total_value, avg_order_value, total_quantity, avg_quantity_per_order, avg_line_items_per_order, cancelled_orders, completed_orders, cancellation_rate, prev_month_orders, prev_month_value, order_count_mom_change, order_value_mom_change
from main_marts.rpt_purchase_order_summary
