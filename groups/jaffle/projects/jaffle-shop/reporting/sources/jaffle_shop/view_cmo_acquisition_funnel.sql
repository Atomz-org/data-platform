-- source extract for view_cmo_acquisition_funnel (PII columns excluded by the MDL projection)
select acquisition_source, customer_count, source_share, source_rank, pct_of_total
from main_marts.view_cmo_acquisition_funnel
