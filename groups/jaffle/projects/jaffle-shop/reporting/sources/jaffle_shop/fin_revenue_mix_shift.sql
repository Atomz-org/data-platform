-- source extract for fin_revenue_mix_shift (PII columns excluded by the MDL projection)
select sale_month, product_type, type_revenue, type_quantity, total_revenue, revenue_share_pct, prev_month_share_pct, share_shift_pct
from main_marts.fin_revenue_mix_shift
