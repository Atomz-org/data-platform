-- source extract for sum_monthly_maintenance_totals (PII columns excluded by the MDL projection)
select maint_month, location_id, event_count, total_cost, avg_cost_per_event, unique_equipment
from main_marts.sum_monthly_maintenance_totals
