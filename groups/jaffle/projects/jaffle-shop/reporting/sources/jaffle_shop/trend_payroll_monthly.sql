-- source extract for trend_payroll_monthly (PII columns excluded by the MDL projection)
select pay_period_start, location_id, total_gross_pay, total_net_pay, employee_count, avg_pay_per_employee, payroll_3m_ma, prev_month_payroll, payroll_mom_change_pct
from main_marts.trend_payroll_monthly
