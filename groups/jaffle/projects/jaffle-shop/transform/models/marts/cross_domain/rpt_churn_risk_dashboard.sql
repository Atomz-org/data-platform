with customer_data as (
    select
        customer_id,
        customer_name,
        lifetime_spend,
        total_orders,
        avg_order_value,
        first_order_at,
        last_order_at,
        days_since_last_order,
        recency_score,
        frequency_score,
        monetary_score,
        rfm_total_score,
        loyalty_member_id,
        loyalty_tier,
        loyalty_points_balance,
        preferred_store_name,
        marketing_engagement_level,
        ltv_tier
    from {{ ref('dim_customer_360') }}
),

order_frequency as (
    select
        customer_id,
        count(distinct order_id) as recent_6m_orders,
        count(distinct order_id) as total_order_count
    from {{ ref('orders') }}
    where ordered_at >= {{ dbt.dateadd("month", -6, "current_timestamp") }}
    group by customer_id
),

historical_frequency as (
    select
        customer_id,
        count(distinct order_id) as prior_6m_orders
    from {{ ref('orders') }}
    where ordered_at >= {{ dbt.dateadd("month", -12, "current_timestamp") }}
        and ordered_at < {{ dbt.dateadd("month", -6, "current_timestamp") }}
    group by customer_id
)

select
    cd.customer_id,
    cd.customer_name,
    cd.lifetime_spend,
    cd.total_orders,
    cd.days_since_last_order,
    cd.rfm_total_score,
    cd.ltv_tier,
    cd.loyalty_tier,
    cd.loyalty_points_balance,
    cd.preferred_store_name,
    cd.marketing_engagement_level,
    coalesce(orf.recent_6m_orders, 0) as orders_last_6_months,
    coalesce(hf.prior_6m_orders, 0) as orders_prior_6_months,
    coalesce(orf.recent_6m_orders, 0) - coalesce(hf.prior_6m_orders, 0) as order_frequency_change,
    case
        when cd.days_since_last_order > 180 and cd.total_orders >= 3 then 'high_risk'
        when cd.days_since_last_order > 90
            and coalesce(orf.recent_6m_orders, 0) < coalesce(hf.prior_6m_orders, 0)
            then 'medium_risk'
        when cd.days_since_last_order > 60 and cd.recency_score <= 2 then 'watch'
        else 'active'
    end as churn_risk_level,
    case
        when cd.ltv_tier in ('platinum', 'gold') then 'high'
        when cd.ltv_tier = 'silver' then 'medium'
        else 'low'
    end as customer_value_priority,
    case
        when cd.loyalty_member_id is not null and cd.loyalty_points_balance > 100
            then 'points_reminder'
        when cd.marketing_engagement_level = 'no_engagement'
            then 'reactivation_campaign'
        when coalesce(orf.recent_6m_orders, 0) < coalesce(hf.prior_6m_orders, 0)
            then 'win_back_offer'
        else 'standard_outreach'
    end as recommended_action
from customer_data as cd
left join order_frequency as orf
    on cd.customer_id = orf.customer_id
left join historical_frequency as hf
    on cd.customer_id = hf.customer_id
where cd.days_since_last_order > 30
    or coalesce(orf.recent_6m_orders, 0) < coalesce(hf.prior_6m_orders, 0)
