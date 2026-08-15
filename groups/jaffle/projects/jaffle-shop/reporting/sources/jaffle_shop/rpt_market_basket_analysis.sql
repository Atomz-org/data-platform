-- source extract for rpt_market_basket_analysis (PII columns excluded by the MDL projection)
select product_a_id, product_b_id, pair_frequency, pair_rank, product_a_name, product_b_name
from main_marts.rpt_market_basket_analysis
