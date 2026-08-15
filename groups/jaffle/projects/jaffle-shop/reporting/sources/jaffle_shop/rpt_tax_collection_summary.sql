-- source extract for rpt_tax_collection_summary (PII columns excluded by the MDL projection)
select jurisdiction, tax_type, tax_rate_pct, location_id, location_name, tax_month, invoice_count, taxable_amount, tax_collected, effective_tax_rate, cumulative_tax_collected
from main_marts.rpt_tax_collection_summary
