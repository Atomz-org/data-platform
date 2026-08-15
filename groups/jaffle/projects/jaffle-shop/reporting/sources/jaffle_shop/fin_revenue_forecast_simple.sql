-- source extract for fin_revenue_forecast_simple (PII columns excluded by the MDL projection)
select location_id, store_name, n_months, avg_revenue, slope, intercept, last_month, forecast_month_1, forecast_month_2, forecast_month_3, monthly_growth_rate_pct
from main_marts.fin_revenue_forecast_simple
