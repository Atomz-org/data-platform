-- source extract for narrow_store_count_by_status (PII columns excluded by the MDL projection)
select is_open, store_count
from main_marts.narrow_store_count_by_status
