-- source extract for adv_category_hierarchy (PII columns excluded by the MDL projection)
select category_id, category_name, parent_category, depth, full_path
from main_marts.adv_category_hierarchy
