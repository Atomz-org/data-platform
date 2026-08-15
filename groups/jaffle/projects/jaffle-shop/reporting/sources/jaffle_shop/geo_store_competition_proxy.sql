-- source extract for geo_store_competition_proxy (PII columns excluded by the MDL projection)
select location_id, month_start, monthly_revenue, mom_growth_pct, rolling_6m_avg_growth, rolling_12m_avg_growth, competition_signal
from main_marts.geo_store_competition_proxy
