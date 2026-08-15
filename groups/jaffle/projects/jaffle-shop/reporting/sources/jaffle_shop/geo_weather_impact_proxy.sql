-- source extract for geo_weather_impact_proxy (PII columns excluded by the MDL projection)
select location_id, calendar_month, avg_monthly_revenue, avg_deviation_from_annual, avg_pct_deviation, seasonality_classification
from main_marts.geo_weather_impact_proxy
