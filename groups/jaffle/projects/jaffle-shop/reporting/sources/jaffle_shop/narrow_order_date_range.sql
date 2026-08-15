-- source extract for narrow_order_date_range (PII columns excluded by the MDL projection)
select min_date, max_date
from main_marts.narrow_order_date_range
