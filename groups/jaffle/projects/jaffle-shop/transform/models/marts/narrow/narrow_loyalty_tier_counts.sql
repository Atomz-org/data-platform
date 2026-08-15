select
    current_tier_name as tier_name,
    count(*) as member_count
from {{ ref('dim_loyalty_members') }}
group by current_tier_name
