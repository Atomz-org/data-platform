-- source extract for sum_monthly_supplier_totals (PII columns excluded by the MDL projection)
select order_month, supplier_id, total_spend, count_purchase_orders, avg_po_value, prior_month_spend
from main_marts.sum_monthly_supplier_totals
