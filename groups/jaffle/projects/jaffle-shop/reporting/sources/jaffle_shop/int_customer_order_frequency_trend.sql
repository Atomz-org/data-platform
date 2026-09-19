-- source extract for int_customer_order_frequency_trend (PII columns excluded by the MDL projection)
-- Columns are enumerated, never `select *`: the extract's shape is a
-- contract with the pages reading it, and a star changes shape silently.
select
    customer_id,
    order_month,
    monthly_order_count,
    order_count_3m_avg,
    monthly_trend_direction,
    trend_acceleration
from main_marts.int_customer_order_frequency_trend
