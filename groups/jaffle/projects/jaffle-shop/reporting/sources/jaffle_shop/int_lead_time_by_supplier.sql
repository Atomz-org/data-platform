-- source extract for int_lead_time_by_supplier (PII columns excluded by the MDL projection)
select supplier_id, count_completed_orders, avg_lead_time_days, avg_lead_time_variance_days, on_time_delivery_rate, min_lead_time_days, max_lead_time_days, avg_expected_lead_time_days, count_on_time_deliveries
from main_marts.int_lead_time_by_supplier
