-- source extract for fin_gift_card_breakage (PII columns excluded by the MDL projection)
select gift_card_id, customer_id, initial_balance, latest_balance, total_redeemed, issued_date, expires_date, last_redemption_date, days_since_issued, days_since_last_use, breakage_risk_category, estimated_breakage_amount, expected_future_redemption
from main_marts.fin_gift_card_breakage
