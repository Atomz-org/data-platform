-- source extract for scr_supplier_reliability (PII columns excluded by the MDL projection)
select supplier_id, reliability_score, reliability_tier, supplier_name, is_active, active_contracts, delivery_score, quality_component_score, price_stability_score, lead_time_consistency_score, on_time_rate, quality_score, defect_rate, avg_lead_time_days, avg_lead_time_variance_days
from main_marts.scr_supplier_reliability
