with journey as (
    select
        customer_id,
        customer_name,
        acquisition_source,
        first_order_at,
        last_order_at,
        total_orders,
        lifetime_spend,
        loyalty_member_id,
        loyalty_enrolled_at,
        loyalty_tier,
        loyalty_lifecycle_stage,
        loyalty_points_balance,
        ltv_tier,
        rfm_total_score,
        days_since_last_order,
        customer_tenure_days,
        preferred_store_name,
        marketing_engagement_level,
        campaigns_responded_to
    from {{ ref('dim_customer_360') }}
)

select
    customer_id,
    customer_name,

    -- Acquisition
    coalesce(acquisition_source, 'unknown') as acquisition_source,
    first_order_at,

    -- Engagement milestones
    total_orders,
    case
        when total_orders >= 2 then true
        else false
    end as is_repeat_customer,
    case
        when total_orders >= 5 then true
        else false
    end as is_frequent_buyer,

    -- Loyalty journey
    loyalty_member_id is not null as is_loyalty_member,
    loyalty_enrolled_at,
    case
        when loyalty_enrolled_at is not null
            then {{ dbt.datediff("first_order_at", "loyalty_enrolled_at", "day") }}
        else null
    end as days_to_loyalty_enrollment,
    loyalty_tier,
    loyalty_lifecycle_stage,
    loyalty_points_balance,

    -- Current status
    lifetime_spend,
    ltv_tier,
    rfm_total_score,
    days_since_last_order,
    customer_tenure_days,
    preferred_store_name,
    marketing_engagement_level,
    campaigns_responded_to,

    -- Journey stage classification
    case
        when total_orders = 1 and days_since_last_order <= 30 then 'new_buyer'
        when total_orders = 1 and days_since_last_order > 30 then 'one_and_done'
        when total_orders >= 2 and loyalty_member_id is null then 'repeat_not_enrolled'
        when loyalty_member_id is not null and loyalty_tier in ('gold', 'platinum') then 'loyal_advocate'
        when loyalty_member_id is not null then 'loyalty_engaged'
        when days_since_last_order > 180 then 'lapsed'
        else 'active'
    end as journey_stage
from journey
