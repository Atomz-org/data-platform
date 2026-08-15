-- source extract for wide_supplier_summary (PII columns excluded by the MDL projection)
select supplier_id, supplier_name, contact_email, total_spend, total_orders, quality_score, avg_lead_time_days, fulfillment_rate, defect_rate, supplier_tier
from main_marts.wide_supplier_summary
