-- source extract for sc_supply_risk_assessment (PII columns excluded by the MDL projection)
select product_id, active_suppliers, source_risk, price_volatility, lead_time_risk, composite_risk_score, overall_risk_level
from main_marts.sc_supply_risk_assessment
