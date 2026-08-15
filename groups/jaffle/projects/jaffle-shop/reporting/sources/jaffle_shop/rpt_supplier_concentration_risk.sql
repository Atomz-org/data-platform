-- source extract for rpt_supplier_concentration_risk (PII columns excluded by the MDL projection)
select supplier_id, supplier_name, is_active, total_contracts, active_contracts, lifetime_spend, avg_spend_share_pct, max_spend_share_pct, active_months, concentration_risk_level, is_concentration_risk
from main_marts.rpt_supplier_concentration_risk
