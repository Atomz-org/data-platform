-- source extract for rpt_labor_efficiency (PII columns excluded by the MDL projection)
select location_id, report_month, monthly_labor_hours, monthly_labor_cost, monthly_revenue, monthly_labor_cost_pct, monthly_revenue_per_labor_hour, avg_daily_staff_count
from main_marts.rpt_labor_efficiency
