-- source extract for rpt_competitive_positioning (PII columns excluded by the MDL projection)
select location_id, competitive_position, store_name, avg_monthly_revenue, avg_operating_margin_pct, store_health_score, company_avg_monthly_revenue, company_avg_margin, revenue_index_vs_company
from main_marts.rpt_competitive_positioning
