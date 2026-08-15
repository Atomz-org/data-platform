-- source extract for fin_customer_profitability (PII columns excluded by the MDL projection)
select customer_id, total_revenue, profitability_tier
from main_marts.fin_customer_profitability
