-- source extract for dim_tax_rates (PII columns excluded by the MDL projection)
select tax_rate_id, jurisdiction, tax_type, tax_rate_pct, effective_from_date, effective_to_date, is_current
from main_marts.dim_tax_rates
