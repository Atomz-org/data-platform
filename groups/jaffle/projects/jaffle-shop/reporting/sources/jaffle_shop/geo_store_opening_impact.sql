-- source extract for geo_store_opening_impact (PII columns excluded by the MDL projection)
select existing_store_id, new_store_id, new_store_name, opening_month, avg_revenue_3m_before, avg_revenue_3m_after, revenue_change, pct_revenue_change, impact_classification
from main_marts.geo_store_opening_impact
