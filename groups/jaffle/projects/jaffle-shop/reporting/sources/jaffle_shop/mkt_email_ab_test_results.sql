-- source extract for mkt_email_ab_test_results (PII columns excluded by the MDL projection)
select campaign_id, test_variant, sent_count, open_count, click_count, unsub_count, open_rate_pct, click_rate_pct, unsub_rate_pct, open_rate_rank
from main_marts.mkt_email_ab_test_results
