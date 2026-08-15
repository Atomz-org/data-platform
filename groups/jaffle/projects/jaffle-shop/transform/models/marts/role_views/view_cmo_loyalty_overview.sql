with

loyalty_health as (
    select * from {{ ref('rpt_loyalty_program_health') }}
)

select
    current_tier_name,
    member_count,
    active_members,
    program_total_members,
    program_active_members,
    program_redemption_rate as redemption_rate_pct,
    round(active_members * 100.0 / nullif(member_count, 0), 2) as active_member_pct,
    case
        when active_members * 100.0 / nullif(member_count, 0) > 60 then 'highly_engaged'
        when active_members * 100.0 / nullif(member_count, 0) > 40 then 'moderately_engaged'
        else 'low_engagement'
    end as program_engagement_level
from loyalty_health
