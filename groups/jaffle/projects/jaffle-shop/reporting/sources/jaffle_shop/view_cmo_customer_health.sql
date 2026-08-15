-- source extract for view_cmo_customer_health (PII columns excluded by the MDL projection)
select reporting_month, tracked_active_customers, churned_customers, customer_health_index, overall_customer_health
from main_marts.view_cmo_customer_health
