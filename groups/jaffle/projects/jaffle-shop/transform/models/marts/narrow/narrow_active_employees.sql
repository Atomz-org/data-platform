select count(*) as active_employee_count
from {{ ref('dim_employees') }}
where is_active = true
