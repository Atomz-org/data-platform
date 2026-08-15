-- source extract for locations (PII columns excluded by the MDL projection)
select location_id, location_name, tax_rate, opened_date
from main_marts.locations
