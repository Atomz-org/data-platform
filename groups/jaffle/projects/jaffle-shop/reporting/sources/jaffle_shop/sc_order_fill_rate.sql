-- source extract for sc_order_fill_rate (PII columns excluded by the MDL projection)
select order_month, location_id, total_orders, fully_filled_orders, order_fill_rate_pct, avg_line_fill_rate_pct
from main_marts.sc_order_fill_rate
