-- source extract for dist_gift_card_balance (PII columns excluded by the MDL projection)
select balance_bucket, card_count, bucket_total, mean_balance, median_balance, total_outstanding, total_cards
from main_marts.dist_gift_card_balance
