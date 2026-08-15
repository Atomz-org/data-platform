-- source extract for rpt_innovation_pipeline (PII columns excluded by the MDL projection)
select season_name, total_units_sold, total_revenue, promotion_name, product_count, units_sold, daily_revenue, avg_revenue_per_product, season_start, season_end
from main_marts.rpt_innovation_pipeline
