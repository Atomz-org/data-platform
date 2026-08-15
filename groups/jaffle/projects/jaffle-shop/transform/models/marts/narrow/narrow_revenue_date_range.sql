select
    min(revenue_date) as first_revenue_date,
    max(revenue_date) as last_revenue_date
from {{ ref('int_daily_revenue') }}
