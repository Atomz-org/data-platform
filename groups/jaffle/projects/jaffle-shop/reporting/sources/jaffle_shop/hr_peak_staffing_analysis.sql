-- source extract for hr_peak_staffing_analysis (PII columns excluded by the MDL projection)
select location_id, order_hour, avg_hourly_orders, avg_hourly_revenue, staff_count, orders_per_staff, demand_period
from main_marts.hr_peak_staffing_analysis
