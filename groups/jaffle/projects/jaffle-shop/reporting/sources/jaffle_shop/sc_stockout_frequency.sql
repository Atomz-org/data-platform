-- source extract for sc_stockout_frequency (PII columns excluded by the MDL projection)
select product_id, location_id, total_days_tracked, stockout_days, in_stock_days, stockout_frequency_pct, first_stockout_date, last_stockout_date, stockout_severity
from main_marts.sc_stockout_frequency
