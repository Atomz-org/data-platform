-- source extract for rpt_revenue_driver_decomposition (PII columns excluded by the MDL projection)
select location_id, revenue_month, traffic_change, frequency_change, ticket_change, total_revenue, prev_revenue, revenue_change, unique_customers, orders_per_customer, avg_ticket_size
from main_marts.rpt_revenue_driver_decomposition
