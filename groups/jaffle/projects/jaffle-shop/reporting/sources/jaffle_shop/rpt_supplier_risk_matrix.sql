-- source extract for rpt_supplier_risk_matrix (PII columns excluded by the MDL projection)
select supplier_id, supplier_name, is_active, total_spend, avg_monthly_spend, spend_concentration_pct, spend_rank, avg_lead_time_days, lead_time_variability, min_lead_time_days, max_lead_time_days, quality_score, defect_rate, concentration_risk_score, reliability_risk_score, quality_risk_score, composite_risk_score, overall_risk_level
from main_marts.rpt_supplier_risk_matrix
