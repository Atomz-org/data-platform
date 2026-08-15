-- source extract for rpt_tax_rate_impact (PII columns excluded by the MDL projection)
select jurisdiction, tax_type, tax_rate_pct, location_id, location_name, tax_month, invoice_count, taxable_amount, tax_collected, effective_tax_rate, rate_variance, total_with_tax, tax_burden_pct, avg_effective_rate_for_jurisdiction, cumulative_tax_collected, jurisdiction_rank_by_tax
from main_marts.rpt_tax_rate_impact
