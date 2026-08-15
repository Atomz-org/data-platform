-- source extract for int_product_margin_trend (PII columns excluded by the MDL projection)
select sale_month, product_id, product_name, product_type, monthly_units_sold, monthly_revenue, gross_margin, gross_margin_pct, monthly_gross_profit, margin_pct_change, avg_selling_price, total_ingredient_cost, prev_month_margin_pct
from main_marts.int_product_margin_trend
