-- source extract for rpt_gross_margin_analysis (PII columns excluded by the MDL projection)
select category_name, products_in_category, category_revenue, category_cogs, category_gross_margin, avg_margin_pct, min_margin_pct, max_margin_pct
from main_marts.rpt_gross_margin_analysis
