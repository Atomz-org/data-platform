-- source extract for hr_employee_cost_per_order (PII columns excluded by the MDL projection)
select employee_id, pay_month, monthly_gross_pay, orders_handled, cost_per_order, labor_cost_per_order
from main_marts.hr_employee_cost_per_order
