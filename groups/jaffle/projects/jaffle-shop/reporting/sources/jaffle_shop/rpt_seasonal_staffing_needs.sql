-- source extract for rpt_seasonal_staffing_needs (PII columns excluded by the MDL projection)
select location_id, month_number, month_name, season, avg_monthly_orders, avg_monthly_revenue, demand_index, demand_classification, current_avg_labor_hours, current_avg_staff, recommended_staff_count
from main_marts.rpt_seasonal_staffing_needs
