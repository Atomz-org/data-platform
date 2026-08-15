-- source extract for fin_cost_allocation_by_product (PII columns excluded by the MDL projection)
select product_id, product_revenue, revenue_share, allocated_overhead, product_contribution, contribution_margin_pct
from main_marts.fin_cost_allocation_by_product
