-- source extract for poc_avg_ticket_yoy (PII columns excluded by the MDL projection)
select month_start, location_id, current_avg_ticket, prior_year_avg_ticket, ticket_yoy_pct
from main_marts.poc_avg_ticket_yoy
