-- source extract for rpt_break_even_by_store (PII columns excluded by the MDL projection)
select location_id, store_name, report_month, monthly_revenue, fixed_costs, variable_costs, contribution_margin, contribution_margin_pct, break_even_revenue, margin_of_safety, margin_of_safety_pct, break_even_status
from main_marts.rpt_break_even_by_store
