-- source extract for int_revenue_by_product_daily (PII columns excluded by the MDL projection)
select revenue_date, product_id, product_name, product_type, units_sold, product_revenue, avg_unit_price, revenue_per_unit, invoice_count, avg_line_total
from main_marts.int_revenue_by_product_daily
