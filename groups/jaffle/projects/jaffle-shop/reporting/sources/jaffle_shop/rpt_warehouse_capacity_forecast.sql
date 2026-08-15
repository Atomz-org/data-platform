-- source extract for rpt_warehouse_capacity_forecast (PII columns excluded by the MDL projection)
select warehouse_id, warehouse_name, warehouse_type, capacity_units, is_active, current_units_stored, distinct_products, current_utilization_rate, remaining_capacity, avg_monthly_growth_units, months_of_data, months_until_full, estimated_full_date
from main_marts.rpt_warehouse_capacity_forecast
