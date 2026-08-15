-- source extract for rpt_vendor_management_summary (PII columns excluded by the MDL projection)
select supplier_id, vendor_classification, supplier_name, is_active, reliability_score, reliability_tier, total_spend, total_purchase_orders, active_months, avg_total_spend
from main_marts.rpt_vendor_management_summary
