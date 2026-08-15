-- source extract for mkt_customer_win_back (PII columns excluded by the MDL projection)
select customer_id, rfm_segment, total_orders, first_order_at, last_order_at, lapse_count, max_gap_days, first_coupon_after_lapse, coupons_used, win_back_trigger
from main_marts.mkt_customer_win_back
