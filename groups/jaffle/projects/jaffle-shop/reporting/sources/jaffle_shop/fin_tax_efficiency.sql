-- source extract for fin_tax_efficiency (PII columns excluded by the MDL projection)
select jurisdiction, tax_month, tax_collected, taxable_amount, CASE  WHEN ((tc.taxable_amount > 0)) THEN ((tc.tax_collected / tc.taxable_amount)) ELSE 0 END, statutory_rate, rate_gap, implied_tax_leakage, efficiency_status
from main_marts.fin_tax_efficiency
