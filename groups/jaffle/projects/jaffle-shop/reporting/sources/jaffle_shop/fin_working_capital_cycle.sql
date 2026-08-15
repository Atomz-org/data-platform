-- source extract for fin_working_capital_cycle (PII columns excluded by the MDL projection)
select report_month, avg_days_receivable, days_inventory_on_hand, avg_days_payable, cash_conversion_cycle_days
from main_marts.fin_working_capital_cycle
