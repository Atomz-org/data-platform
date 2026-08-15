-- source extract for rpt_financial_health_scorecard (PII columns excluded by the MDL projection)
select location_id, location_name, report_month, total_revenue, revenue_growth_rate, total_expenses, expense_ratio, refund_rate, refund_amount_rate, revenue_growth_score, expense_ratio_score, refund_rate_score, profitability_score, health_score, health_grade
from main_marts.rpt_financial_health_scorecard
