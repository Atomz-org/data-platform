-- source extract for rpt_360_product_portfolio_review (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    product_id,
    portfolio_quadrant,
    viability_tier
from main_marts.rpt_360_product_portfolio_review
