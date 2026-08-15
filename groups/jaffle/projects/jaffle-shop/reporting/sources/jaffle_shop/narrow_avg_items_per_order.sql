-- source extract for narrow_avg_items_per_order (PII columns excluded by the MDL projection)
select avg_items, median_items
from main_marts.narrow_avg_items_per_order
