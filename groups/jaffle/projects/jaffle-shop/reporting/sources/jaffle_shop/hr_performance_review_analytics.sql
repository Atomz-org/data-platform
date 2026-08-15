-- source extract for hr_performance_review_analytics (PII columns excluded by the MDL projection)
select department_name, review_quarter, review_count, avg_score, min_score, max_score, high_performers, underperformers, high_performer_pct, prev_quarter_avg, score_trend
from main_marts.hr_performance_review_analytics
