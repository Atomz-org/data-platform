-- source extract for rpt_first_purchase_attribution (PII columns excluded by the MDL projection)
select attribution_channel, acquisition_source, customers, total_first_order_revenue, avg_first_order_value, earliest_first_purchase, latest_first_purchase, customer_share
from main_marts.rpt_first_purchase_attribution
