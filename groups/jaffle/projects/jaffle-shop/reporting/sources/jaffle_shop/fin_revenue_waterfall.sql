-- source extract for fin_revenue_waterfall (PII columns excluded by the MDL projection)
select revenue_month, opening_balance, new_customer_revenue, upsell_revenue, stable_returning_revenue, downsell_impact, implied_churn_revenue, closing_balance
from main_marts.fin_revenue_waterfall
