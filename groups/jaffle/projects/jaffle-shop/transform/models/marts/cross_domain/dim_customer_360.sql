with base_customers as (
    select
        customer_id,
        customer_name
    from {{ ref('customers') }}
),

ltv as (
    select * from {{ ref('int_customer_ltv') }}
),

rfm as (
    select * from {{ ref('int_customer_rfm_scores') }}
),

loyalty as (
    select * from {{ ref('int_customer_loyalty_enriched') }}
),

preferred_store as (
    select * from {{ ref('int_customer_preferred_store') }}
),

preferred_products as (
    select * from {{ ref('int_customer_preferred_products') }}
),

marketing as (
    select * from {{ ref('int_customer_marketing_response') }}
)

select
    bc.customer_id,
    bc.customer_name,

    -- LTV metrics
    ltv.lifetime_spend,
    ltv.total_orders,
    ltv.avg_order_value,
    ltv.first_order_at,
    ltv.last_order_at,
    ltv.customer_tenure_days,
    ltv.ltv_tier,

    -- RFM scores
    rfm.days_since_last_order,
    rfm.recency_score,
    rfm.frequency_score,
    rfm.monetary_score,
    rfm.rfm_total_score,
    rfm.rfm_segment_code,

    -- Loyalty
    loyalty.member_id as loyalty_member_id,
    loyalty.current_tier as loyalty_tier,
    loyalty.loyalty_enrolled_at,
    loyalty.membership_tenure_days as loyalty_tenure_days,
    loyalty.loyalty_points_balance,
    loyalty.loyalty_lifecycle_stage,

    -- Preferred store
    ps.preferred_store_id,
    ps.preferred_store_name,
    ps.preferred_store_visits,
    ps.preferred_store_visit_pct,
    ps.distinct_stores_visited,

    -- Preferred products
    pp.top1_product_id,
    pp.top1_product_name,
    pp.top1_purchase_count,
    pp.top1_product_share_pct,
    pp.top2_product_id,
    pp.top2_product_name,
    pp.top3_product_id,
    pp.top3_product_name,
    pp.total_items_purchased,

    -- Marketing
    marketing.total_coupons_redeemed,
    marketing.campaigns_responded_to,
    marketing.campaign_response_rate_pct,
    marketing.total_discount_received,
    marketing.acquisition_source,
    marketing.marketing_engagement_level

from base_customers as bc
left join ltv
    on bc.customer_id = ltv.customer_id
left join rfm
    on bc.customer_id = rfm.customer_id
left join loyalty
    on bc.customer_id = loyalty.customer_id
left join preferred_store as ps
    on bc.customer_id = ps.customer_id
left join preferred_products as pp
    on bc.customer_id = pp.customer_id
left join marketing
    on bc.customer_id = marketing.customer_id
