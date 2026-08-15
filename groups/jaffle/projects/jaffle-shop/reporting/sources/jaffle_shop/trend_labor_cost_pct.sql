-- source extract for trend_labor_cost_pct (PII columns excluded by the MDL projection)
select work_date, location_id, labor_cost_pct, labor_cost_pct_7d_ma, labor_cost_pct_28d_ma, labor_cost_band
from main_marts.trend_labor_cost_pct
