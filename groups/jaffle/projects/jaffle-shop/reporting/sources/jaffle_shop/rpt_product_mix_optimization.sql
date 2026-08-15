-- source extract for rpt_product_mix_optimization (PII columns excluded by the MDL projection)
select product_id, product_name, product_type, total_units_sold, total_revenue, active_sale_days, avg_daily_units, revenue_contribution_pct, revenue_rank, volume_rank, top_paired_product_id, top_pair_co_occurrences, top_pair_support, product_classification
from main_marts.rpt_product_mix_optimization
