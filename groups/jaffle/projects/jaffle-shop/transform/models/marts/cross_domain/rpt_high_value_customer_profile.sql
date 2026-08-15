with ranked_customers as (
    select
        customer_id,
        customer_name,
        lifetime_spend,
        total_orders,
        avg_order_value,
        first_order_at,
        last_order_at,
        customer_tenure_days,
        days_since_last_order,
        ltv_tier,
        rfm_total_score,
        recency_score,
        frequency_score,
        monetary_score,
        loyalty_tier,
        loyalty_points_balance,
        loyalty_lifecycle_stage,
        preferred_store_name,
        preferred_store_visit_pct,
        distinct_stores_visited,
        top1_product_name,
        top1_product_share_pct,
        top2_product_name,
        top3_product_name,
        total_items_purchased,
        acquisition_source,
        marketing_engagement_level,
        total_coupons_redeemed,
        campaign_response_rate_pct,
        total_discount_received,
        percent_rank() over (order by lifetime_spend asc) as spend_percentile
    from {{ ref('dim_customer_360') }}
)

select
    customer_id,
    customer_name,
    lifetime_spend,
    total_orders,
    avg_order_value,
    first_order_at,
    last_order_at,
    customer_tenure_days,
    days_since_last_order,
    ltv_tier,
    rfm_total_score,
    loyalty_tier,
    loyalty_points_balance,
    loyalty_lifecycle_stage,
    preferred_store_name,
    preferred_store_visit_pct,
    distinct_stores_visited,
    top1_product_name as favorite_product,
    top2_product_name as second_favorite_product,
    top3_product_name as third_favorite_product,
    total_items_purchased,
    acquisition_source,
    marketing_engagement_level,
    total_coupons_redeemed,
    campaign_response_rate_pct,
    total_discount_received,
    round(cast(spend_percentile * 100 as {{ dbt.type_float() }}), 2) as spend_percentile_rank,
    case
        when days_since_last_order <= 30 then 'active'
        when days_since_last_order <= 90 then 'cooling'
        else 'at_risk'
    end as engagement_status,
    round(
        (cast(lifetime_spend as {{ dbt.type_float() }})
        / nullif(customer_tenure_days, 0) * 30), 2
    ) as monthly_spend_rate
from ranked_customers
where spend_percentile >= 0.90
