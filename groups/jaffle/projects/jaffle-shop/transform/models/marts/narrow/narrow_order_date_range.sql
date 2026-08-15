select
    min(ordered_at) as min_date,
    max(ordered_at) as max_date
from {{ ref('stg_orders') }}
