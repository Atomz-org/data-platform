-- source extract for rpt_customer_acquisition_funnel (PII columns excluded by the MDL projection)
select acquisition_source, total_customers, customers_with_campaign, customers_from_referral, source_share, source_rank
from main_marts.rpt_customer_acquisition_funnel
