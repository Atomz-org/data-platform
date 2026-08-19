-- source extract for rpt_market_basket_analysis (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_a_id,
    product_b_id,
    pair_frequency,
    pair_rank
from main_marts.rpt_market_basket_analysis
