select
    location_id,
    store_name as location_name,
    sum(monthly_revenue) as total_revenue
from {{ ref('met_monthly_revenue_by_store') }}
group by location_id, store_name
order by total_revenue desc
limit 10
