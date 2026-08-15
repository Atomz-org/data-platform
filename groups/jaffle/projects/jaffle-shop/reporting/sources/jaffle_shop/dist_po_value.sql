-- source extract for dist_po_value (PII columns excluded by the MDL projection)
select value_bucket, po_count, bucket_total, mean_value, median_value, total_pos
from main_marts.dist_po_value
