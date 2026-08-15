-- source extract for fin_seasonal_budget_adjustment (PII columns excluded by the MDL projection)
select calendar_month, avg_month_revenue, avg_annual_monthly, seasonal_factor, season_classification, budget_multiplier
from main_marts.fin_seasonal_budget_adjustment
