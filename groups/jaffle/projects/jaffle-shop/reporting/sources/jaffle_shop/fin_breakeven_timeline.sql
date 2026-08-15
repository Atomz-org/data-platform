-- source extract for fin_breakeven_timeline (PII columns excluded by the MDL projection)
select location_id, store_name, opened_date, months_to_breakeven, breakeven_date, latest_cumulative_profit, total_months, breakeven_status, estimated_months_to_breakeven
from main_marts.fin_breakeven_timeline
