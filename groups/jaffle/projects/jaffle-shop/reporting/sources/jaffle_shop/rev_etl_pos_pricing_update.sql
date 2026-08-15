-- source extract for rev_etl_pos_pricing_update (PII columns excluded by the MDL projection)
select product_id, current_price, previous_price, price_price_changed_date, price_change, price_change_pct, exported_at
from main_marts.rev_etl_pos_pricing_update
