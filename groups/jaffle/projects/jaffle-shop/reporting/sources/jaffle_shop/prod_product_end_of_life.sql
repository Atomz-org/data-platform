-- source extract for prod_product_end_of_life (PII columns excluded by the MDL projection)
select product_id, product_name, recent_3m_qty, prior_3m_qty, earlier_6m_qty, months_of_data, recent_vs_prior_growth_pct, lifecycle_status
from main_marts.prod_product_end_of_life
