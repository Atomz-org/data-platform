-- source extract for rpt_360_product_portfolio_review (PII columns excluded by the MDL projection)
select product_id, portfolio_quadrant, viability_tier, product_name, product_type, units_sold, total_revenue, gross_margin, gross_margin_pct, viability_score
from main_marts.rpt_360_product_portfolio_review
