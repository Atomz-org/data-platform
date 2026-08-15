-- source extract for fin_operating_leverage (PII columns excluded by the MDL projection)
select location_id, location_name, expense_month, fixed_costs, variable_costs, semi_variable_costs, total_costs, fixed_cost_pct, variable_cost_pct, operating_leverage_ratio
from main_marts.fin_operating_leverage
