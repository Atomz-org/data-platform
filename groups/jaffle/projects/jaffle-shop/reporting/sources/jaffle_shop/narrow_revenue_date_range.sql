-- source extract for narrow_revenue_date_range (PII columns excluded by the MDL projection)
select first_revenue_date, last_revenue_date
from main_marts.narrow_revenue_date_range
