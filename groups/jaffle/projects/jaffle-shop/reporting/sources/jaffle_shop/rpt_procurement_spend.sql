-- source extract for rpt_procurement_spend (PII columns excluded by the MDL projection)
select supplier_id, supplier_name, order_month, total_spend, count_purchase_orders, total_quantity_ordered, avg_unit_cost, total_monthly_spend, spend_share_of_month
from main_marts.rpt_procurement_spend
