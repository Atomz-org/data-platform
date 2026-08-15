-- Total company revenue should always be positive
select 1
from {{ ref('exec_company_kpis_monthly') }}
where monthly_revenue <= 0
