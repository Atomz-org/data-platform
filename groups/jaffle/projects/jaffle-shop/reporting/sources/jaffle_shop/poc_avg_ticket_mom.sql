-- source extract for poc_avg_ticket_mom (PII columns excluded by the MDL projection)
select month_start, location_id, current_avg_ticket, prior_month_avg_ticket, ticket_mom_pct
from main_marts.poc_avg_ticket_mom
