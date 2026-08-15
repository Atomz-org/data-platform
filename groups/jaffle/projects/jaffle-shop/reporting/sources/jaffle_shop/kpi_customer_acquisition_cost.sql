-- source extract for kpi_customer_acquisition_cost (PII columns excluded by the MDL projection)
select month_start, marketing_spend, new_customers, cac
from main_marts.kpi_customer_acquisition_cost
