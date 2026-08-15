-- source extract for sc_bulk_discount_analysis (PII columns excluded by the MDL projection)
select product_id, order_size_bucket, order_count, avg_unit_cost, total_quantity, total_spend, small_order_avg_cost, savings_vs_small_pct, total_savings_vs_small
from main_marts.sc_bulk_discount_analysis
