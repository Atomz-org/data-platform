-- source extract for rpt_supplier_scorecard (PII columns excluded by the MDL projection)
select supplier_id, supplier_name, lifetime_spend, avg_monthly_spend, active_months, total_purchase_orders, fulfillment_rate, fully_fulfilled_orders, partially_fulfilled_orders, avg_lead_time_days, avg_lead_time_variance_days, on_time_delivery_rate, count_completed_orders
from main_marts.rpt_supplier_scorecard
