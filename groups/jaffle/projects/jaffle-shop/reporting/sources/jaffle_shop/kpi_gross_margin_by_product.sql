-- source extract for kpi_gross_margin_by_product (PII columns excluded by the MDL projection)
select product_id, sale_month, revenue, cogs, gross_profit, gross_margin_pct
from main_marts.kpi_gross_margin_by_product
