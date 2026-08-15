-- source extract for rpt_category_contribution_trend (PII columns excluded by the MDL projection)
select sale_month, menu_category_id, category_name, monthly_units_sold, monthly_revenue, total_monthly_revenue, revenue_share_pct, prev_month_revenue, revenue_mom_change_pct, prev_month_share_pct, share_change_ppt, share_trend
from main_marts.rpt_category_contribution_trend
