-- source extract for rpt_speed_of_service_proxy (PII columns excluded by the MDL projection)
select store_name, store_id, order_hour, avg_orders_per_hour, employees_present, orders_per_employee_per_hour, est_minutes_per_order, store_avg_orders_per_emp_hr, store_avg_minutes_per_order, fleet_avg_orders_per_emp_hr, fleet_avg_minutes_per_order, throughput_classification
from main_marts.rpt_speed_of_service_proxy
