-- source extract for adv_org_hierarchy (PII columns excluded by the MDL projection)
select employee_id, full_name, manager_id, manager_name, department_name, depth_level, org_path
from main_marts.adv_org_hierarchy
