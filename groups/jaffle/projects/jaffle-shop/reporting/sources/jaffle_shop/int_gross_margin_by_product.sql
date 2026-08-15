-- source extract for int_gross_margin_by_product (PII columns excluded by the MDL projection)
select product_id, gross_margin, gross_margin_pct, units_sold, daily_revenue, avg_revenue_per_unit, cogs_per_unit, total_cogs, gross_margin_per_unit
from main_marts.int_gross_margin_by_product
