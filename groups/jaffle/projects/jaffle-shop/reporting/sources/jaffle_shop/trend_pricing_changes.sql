-- source extract for trend_pricing_changes (PII columns excluded by the MDL projection)
select price_changed_date, changes_count, avg_pct_change, price_increases, price_decreases, changes_28d_ma, pct_change_28d_ma, changes_90d_total
from main_marts.trend_pricing_changes
