-- source extract for int_tax_collected_by_jurisdiction (PII columns excluded by the MDL projection)
select jurisdiction, tax_type, tax_rate_pct, location_id, tax_month, taxable_amount, tax_collected, location_name, invoice_count
from main_marts.int_tax_collected_by_jurisdiction
