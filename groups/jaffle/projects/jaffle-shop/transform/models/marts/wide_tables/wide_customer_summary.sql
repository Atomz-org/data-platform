with

cr as (
    select * from {{ ref('fct_coupon_redemptions') }}
),

customer_360 as (

    select * from {{ ref('dim_customer_360') }}

),

customers_base as (

    select * from {{ ref('customers') }}

),

churn as (

    select * from {{ ref('scr_customer_churn_propensity') }}

),

loyalty as (

    select * from {{ ref('dim_loyalty_members') }}

),

order_stats as (

    select
        customer_id,
        count(distinct order_id) as total_orders,
        sum(order_total) as total_revenue,
        avg(order_total) as avg_order_value,
        sum(count_order_items) as total_items_ordered,
        avg(count_order_items) as avg_items_per_order,
        sum(case when is_food_order and is_drink_order then 1 else 0 end) as mixed_order_count,
        sum(case when is_food_order and not is_drink_order then 1 else 0 end) as food_only_order_count,
        sum(case when is_drink_order and not is_food_order then 1 else 0 end) as drink_only_order_count,
        sum(tax_paid) as total_tax_paid,
        min(ordered_at) as first_order_date,
        max(ordered_at) as last_order_date

    from {{ ref('orders') }}
    group by customer_id

),

coupon_stats as (

    select
        cr.customer_id,
        count(*) as coupon_usage_count,
        sum(cr.discount_applied) as total_discount_received

    from cr
    group by cr.customer_id

),

store_visits as (

    select
        customer_id,
        count(distinct location_id) as distinct_stores_visited

    from {{ ref('orders') }}
    group by customer_id

)

select
    -- Basic info
    c360.customer_id,
    c360.customer_name,
    cb.customer_type,

    -- Order stats
    os.first_order_date,
    os.last_order_date,
    os.total_orders as lifetime_orders,
    os.total_revenue as lifetime_spend,
    os.avg_order_value,
    {{ dbt.datediff("os.first_order_date", "os.last_order_date", "day") }} as days_as_customer,
    case
        when {{ dbt.datediff("os.first_order_date", "os.last_order_date", "month") }} > 0
        then os.total_orders * 1.0 / {{ dbt.datediff("os.first_order_date", "os.last_order_date", "month") }}
        else os.total_orders
    end as orders_per_month,

    -- RFM
    c360.days_since_last_order as recency_days,
    c360.recency_score,
    c360.frequency_score,
    c360.monetary_score,
    c360.rfm_total_score,
    c360.rfm_segment_code as rfm_segment,

    -- Loyalty
    loy.loyalty_member_id is not null as is_loyalty_member,
    loy.current_tier_name as loyalty_tier,
    loy.current_points_balance as loyalty_points_balance,
    loy.enrolled_at as loyalty_join_date,
    case
        when loy.enrolled_at is not null
        then {{ dbt.datediff("loy.enrolled_at", dbt.current_timestamp(), "day") }}
        else null
    end as loyalty_tenure_days,
    loy.is_active_member as is_loyalty_active,
    loy.total_points_earned as loyalty_total_points_earned,
    loy.total_points_redeemed as loyalty_total_points_redeemed,

    -- Preferences
    c360.preferred_store_id,
    c360.preferred_store_name,
    c360.preferred_store_visits,
    c360.preferred_store_visit_pct,
    c360.distinct_stores_visited,
    c360.top1_product_id as top_product_1_id,
    c360.top1_product_name as top_product_1,
    c360.top2_product_id as top_product_2_id,
    c360.top2_product_name as top_product_2,
    c360.top3_product_id as top_product_3_id,
    c360.top3_product_name as top_product_3,
    c360.top1_purchase_count as top_product_1_purchases,
    c360.top1_product_share_pct as top_product_1_share_pct,
    c360.total_items_purchased,

    -- Behavioral
    os.avg_items_per_order,
    case
        when os.total_orders > 0
        then os.food_only_order_count * 100.0 / os.total_orders
        else 0
    end as pct_food_only_orders,
    case
        when os.total_orders > 0
        then os.drink_only_order_count * 100.0 / os.total_orders
        else 0
    end as pct_drink_only_orders,
    case
        when os.total_orders > 0
        then os.mixed_order_count * 100.0 / os.total_orders
        else 0
    end as pct_mixed_orders,
    os.food_only_order_count,
    os.drink_only_order_count,
    os.mixed_order_count,
    coalesce(cps.coupon_usage_count, 0) > 0 as has_used_coupon,
    coalesce(cps.coupon_usage_count, 0) as coupon_usage_count,
    coalesce(cps.total_discount_received, 0) as total_discount_received,
    sv.distinct_stores_visited as stores_visited_count,

    -- Scoring
    ch.churn_propensity_score,
    ch.churn_risk_tier as churn_risk_level,
    c360.ltv_tier as value_segment,
    c360.customer_tenure_days,

    -- Marketing
    c360.acquisition_source,
    c360.total_coupons_redeemed as marketing_coupons_redeemed,
    c360.campaigns_responded_to,
    c360.campaign_response_rate_pct,
    c360.marketing_engagement_level,

    -- Financial
    os.total_tax_paid as lifetime_tax_paid,
    case
        when {{ dbt.datediff("os.first_order_date", "os.last_order_date", "month") }} > 0
        then os.total_revenue * 1.0 / {{ dbt.datediff("os.first_order_date", "os.last_order_date", "month") }}
        else os.total_revenue
    end as avg_monthly_spend,

    -- Status
    case
        when c360.days_since_last_order <= 90 then true
        else false
    end as is_active,
    case
        when c360.days_since_last_order is not null
        then round(c360.days_since_last_order * 1.0 / 30, 1)
        else null
    end as months_since_last_order,
    case
        when c360.days_since_last_order <= 30 then 'active'
        when c360.days_since_last_order <= 90 then 'engaged'
        when c360.days_since_last_order <= 180 then 'at_risk'
        when c360.days_since_last_order <= 365 then 'dormant'
        else 'churned'
    end as customer_lifecycle_stage,

    -- Loyalty lifecycle
    c360.loyalty_lifecycle_stage,
    c360.loyalty_tier as c360_loyalty_tier,
    c360.loyalty_tenure_days as c360_loyalty_tenure_days

from customer_360 as c360
left join customers_base as cb on c360.customer_id = cb.customer_id
left join order_stats as os on c360.customer_id = os.customer_id
left join churn as ch on c360.customer_id = ch.customer_id
left join loyalty as loy on c360.customer_id = loy.customer_id
left join coupon_stats as cps on c360.customer_id = cps.customer_id
left join store_visits as sv on c360.customer_id = sv.customer_id
