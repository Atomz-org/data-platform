-- source extract for int_accounts_receivable_turnover (PII columns excluded by the MDL projection)
select sales_month, ar_turnover_ratio, days_sales_outstanding, net_credit_sales, avg_ar_balance, total_ar_outstanding, ar_count
from main_marts.int_accounts_receivable_turnover
