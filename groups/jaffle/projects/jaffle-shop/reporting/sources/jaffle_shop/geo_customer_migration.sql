-- source extract for geo_customer_migration (PII columns excluded by the MDL projection)
select order_month, migration_status, customer_count, pct_of_monthly_customers
from main_marts.geo_customer_migration
