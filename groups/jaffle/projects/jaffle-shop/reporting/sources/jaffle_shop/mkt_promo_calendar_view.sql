-- source extract for mkt_promo_calendar_view (PII columns excluded by the MDL projection)
select promo_id, promo_name, promo_type, campaign_start_date, campaign_end_date, promo_source, promo_duration_days, concurrent_promos, overlap_flag
from main_marts.mkt_promo_calendar_view
