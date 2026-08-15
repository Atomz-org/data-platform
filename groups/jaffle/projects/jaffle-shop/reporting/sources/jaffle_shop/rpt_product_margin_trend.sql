-- source extract for rpt_product_margin_trend (PII columns excluded by the MDL projection)
select sale_month, product_id, product_name, product_type, monthly_units_sold, monthly_revenue, avg_selling_price, total_ingredient_cost, gross_margin, gross_margin_pct, monthly_gross_profit, prev_month_margin_pct, margin_pct_change, margin_trend_status, margin_health, rolling_3m_avg_margin_pct
from main_marts.rpt_product_margin_trend
