-- source extract for rpt_risk_register (PII columns excluded by the MDL projection)
select risk_domain, risk_count, risk_description
from main_marts.rpt_risk_register
