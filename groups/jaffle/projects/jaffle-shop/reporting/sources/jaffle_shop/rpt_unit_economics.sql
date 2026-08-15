-- source extract for rpt_unit_economics (PII columns excluded by the MDL projection)
select product_id, gross_margin_pct, contribution_tier, product_name, product_type, units_sold, daily_revenue, revenue_per_unit, cogs_per_unit, gross_margin_per_unit, total_cogs, total_gross_margin
from main_marts.rpt_unit_economics
