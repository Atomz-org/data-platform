{{
    config(
        materialized='table',
        tags=['mega_wide', 'customer_master']
    )
}}

/*
    mega_wide_customer_master
    -------------------------
    One row per customer. The ultimate denormalized customer dimension
    combining order history, loyalty, preferences, coupons, engagement,
    scoring, and trends (80+ columns).
*/

-- ============================================================
-- Base customer identity
-- ============================================================
with

c as (
    select * from {{ ref('customers') }}
),

o as (
    select * from {{ ref('orders') }}
),

oi as (
    select * from {{ ref('stg_order_items') }}
),

p as (
    select * from {{ ref('stg_products') }}
),

r as (
    select * from {{ ref('int_customer_rfm_scores') }}
),

lm as (
    select * from {{ ref('dim_loyalty_members') }}
),

lt as (
    select * from {{ ref('fct_loyalty_transactions') }}
),

l as (
    select * from {{ ref('stg_locations') }}
),

cr as (
    select * from {{ ref('fct_coupon_redemptions') }}
),

pr as (
    select * from {{ ref('stg_product_reviews') }}
),

cas as (
    select * from {{ ref('int_customer_acquisition_source') }}
),

ee as (
    select * from {{ ref('stg_email_events') }}
),

sc as (
    select * from {{ ref('scr_customer_churn_propensity') }}
),

cl as (
    select * from {{ ref('int_customer_ltv') }}
),


customer_base as (

    select
        c.customer_id,
        c.customer_name,
        c.customer_type,
        c.first_ordered_at as customer_since_date
    from c

),

-- ============================================================
-- Order history
-- ============================================================
order_history as (

    select
        o.customer_id,
        min(o.ordered_at)                                                   as first_order_date,
        max(o.ordered_at)                                                   as last_order_date,
        count(distinct o.order_id)                                          as lifetime_orders,
        coalesce(sum(o.order_total), 0)                                     as lifetime_spend,
        avg(o.order_total)                                                  as avg_order_value,
        max(o.order_total)                                                  as max_order_value,
        min(o.order_total)                                                  as min_order_value,
        {{ dbt.datediff('min(o.ordered_at)', 'current_date', 'day') }} as days_as_customer,
        {{ dbt.datediff('max(o.ordered_at)', 'current_date', 'day') }} as days_since_last_order
    from o
    group by 1

),

-- ============================================================
-- Item-level details
-- ============================================================
item_details as (

    select
        o.customer_id,
        count(oi.order_item_id)                                                as total_items_purchased,
        sum(case when p.product_type = 'food' then 1 else 0 end)             as total_food_items,
        sum(case when p.product_type = 'beverage' then 1 else 0 end)         as total_drink_items
    from oi
    inner join o on oi.order_id = o.order_id
    inner join p on oi.product_id = p.product_id
    group by 1

),

-- ============================================================
-- RFM scores
-- ============================================================
rfm as (

    select
        r.customer_id,
        r.recency_score,
        r.frequency_score,
        r.monetary_score,
        r.rfm_segment_code as rfm_segment,
        r.rfm_total_score as rfm_combined_score
    from r

),

-- ============================================================
-- Loyalty
-- ============================================================
loyalty as (

    select
        lm.customer_id,
        true                                                                as is_loyalty_member,
        lm.loyalty_member_id,
        lm.enrolled_at                                                        as loyalty_join_date,
        {{ dbt.datediff('lm.enrolled_at', 'current_date', 'day') }} as loyalty_tenure_days,
        lm.current_tier_name                                                             as loyalty_tier,
        lm.current_points_balance                                                   as loyalty_points_balance,
        lm.membership_status                                                           as loyalty_status
    from lm

),

loyalty_txn_agg as (

    select
        lt.customer_id,
        count(*)                                                            as loyalty_transactions_count,
        sum(case when lt.transaction_type = 'earn' then lt.points else 0 end) as total_points_earned,
        sum(case when lt.transaction_type = 'redeem' then lt.points else 0 end) as total_points_redeemed,
        avg(lt.points)                                                      as avg_points_per_transaction,
        {{ dbt.datediff('max(lt.transacted_at)', 'current_date', 'day') }} as days_since_last_loyalty_activity
    from lt
    group by 1

),

-- ============================================================
-- Store / day-of-week / hour preferences
-- ============================================================
store_preference as (

    select
        customer_id,
        location_id as preferred_store_id,
        location_name as preferred_store_name
    from (
        select
            o.customer_id,
            o.location_id,
            l.location_name,
            row_number() over (partition by o.customer_id order by count(*) desc) as _rn
        from o
        inner join l on o.location_id = l.location_id
        group by o.customer_id, o.location_id, l.location_name
    ) ranked
    where _rn = 1

),

stores_visited as (

    select
        o.customer_id,
        count(distinct o.location_id)                                       as stores_visited_count
    from o
    group by 1

),

day_preference as (

    select
        customer_id,
        preferred_day_of_week
    from (
        select
            o.customer_id,
            {{ day_of_week_number('o.ordered_at') }} as preferred_day_of_week,
            row_number() over (partition by o.customer_id order by count(*) desc) as _rn
        from o
        group by o.customer_id, {{ day_of_week_number('o.ordered_at') }}
    ) ranked
    where _rn = 1

),

hour_preference as (

    select
        customer_id,
        preferred_hour_of_day
    from (
        select
            o.customer_id,
            extract(hour from o.ordered_at) as preferred_hour_of_day,
            row_number() over (partition by o.customer_id order by count(*) desc) as _rn
        from o
        where o.ordered_at is not null
        group by o.customer_id, extract(hour from o.ordered_at)
    ) ranked
    where _rn = 1

),

-- ============================================================
-- Top 3 products per customer
-- ============================================================
product_ranked as (

    select
        o.customer_id,
        oi.product_id,
        p.product_name,
        p.product_type,
        count(oi.order_item_id)                                                as qty,
        row_number() over (
            partition by o.customer_id order by count(oi.order_item_id) desc
        )                                                                   as rn
    from oi
    inner join o on oi.order_id = o.order_id
    inner join p on oi.product_id = p.product_id
    group by o.customer_id, oi.product_id, p.product_name, p.product_type

),

top_products as (

    select
        customer_id,
        max(case when rn = 1 then product_id end)                          as top_product_1_id,
        max(case when rn = 1 then product_name end)                        as top_product_1_name,
        max(case when rn = 2 then product_id end)                          as top_product_2_id,
        max(case when rn = 2 then product_name end)                        as top_product_2_name,
        max(case when rn = 3 then product_id end)                          as top_product_3_id,
        max(case when rn = 3 then product_name end)                        as top_product_3_name,
        max(case when rn = 1 then product_type end)                        as preferred_product_type
    from product_ranked
    where rn <= 3
    group by customer_id

),

-- ============================================================
-- Coupon behavior
-- ============================================================
coupon_behavior as (

    select
        cr.customer_id,
        true                                                                as has_used_coupon,
        count(*)                                                            as total_coupons_used,
        sum(cr.discount_applied)                                             as total_discount_received,
        avg(cr.discount_applied)                                             as avg_discount_per_coupon,
        min(cr.redeemed_at)                                             as first_coupon_date,
        max(cr.redeemed_at)                                             as last_coupon_date,
        max(cr.discount_type)                                                 as favorite_coupon_type_proxy
    from cr
    group by 1

),

coupon_order_pct as (

    select
        o.customer_id,
        count(distinct o.order_id)                                          as total_orders_for_pct,
        count(distinct cr.order_id)                                         as coupon_orders
    from o
    left join cr on o.order_id = cr.order_id
    group by 1

),

-- ============================================================
-- Reviews & engagement
-- ============================================================
reviews as (

    select
        pr.customer_id,
        count(*)                                                            as review_count,
        avg(pr.rating)                                                      as avg_review_score
    from pr
    group by 1

),

acquisition as (

    select
        cas.customer_id,
        cas.acquisition_source
    from cas

),

email_engagement as (

    -- rough proxy: count email opens per customer (if email_events has customer linkage)
    select
        ee.customer_id,
        count(case when ee.email_event_type = 'open' then 1 end)                 as email_engagement_proxy
    from ee
    where ee.customer_id is not null
    group by 1

),

-- ============================================================
-- Scoring
-- ============================================================
churn_score as (

    select
        sc.customer_id,
        sc.churn_propensity_score,
        sc.churn_risk_tier,
        false
    from sc

),

ltv as (

    select
        cl.customer_id,
        cl.lifetime_spend,
        cl.ltv_tier,
        cl.avg_order_value
    from cl

),

-- ============================================================
-- Spend trends (last 3 months vs prior 3 months)
-- ============================================================
monthly_spend as (

    select
        o.customer_id,
        {{ sf_date_trunc('month', "o.ordered_at") }}::date                             as order_month,
        sum(o.order_total)                                                  as monthly_spend,
        count(distinct o.order_id)                                          as monthly_orders,
        avg(o.order_total)                                                  as monthly_aov
    from o
    group by 1, 2

),

spend_trends as (

    select
        ms.customer_id,
        -- Recent 3 months averages
        avg(case when ms.order_month >= (current_date - interval '3 months')::date
                 then ms.monthly_spend end)                                 as avg_spend_recent_3m,
        avg(case when ms.order_month < (current_date - interval '3 months')::date
                  and ms.order_month >= (current_date - interval '6 months')::date
                 then ms.monthly_spend end)                                 as avg_spend_prior_3m,
        avg(case when ms.order_month >= (current_date - interval '3 months')::date
                 then ms.monthly_orders end)                                as avg_orders_recent_3m,
        avg(case when ms.order_month < (current_date - interval '3 months')::date
                  and ms.order_month >= (current_date - interval '6 months')::date
                 then ms.monthly_orders end)                                as avg_orders_prior_3m,
        avg(case when ms.order_month >= (current_date - interval '3 months')::date
                 then ms.monthly_aov end)                                   as avg_aov_recent_3m,
        avg(case when ms.order_month < (current_date - interval '3 months')::date
                  and ms.order_month >= (current_date - interval '6 months')::date
                 then ms.monthly_aov end)                                   as avg_aov_prior_3m,
        -- Months of declining spend (simplified)
        0 as months_of_declining_spend_raw
    from monthly_spend ms
    group by 1

),

-- ============================================================
-- Active flags
-- ============================================================
active_flags as (

    select
        o.customer_id,
        max(case when o.ordered_at >= current_date - 30 then true else false end) as is_active_last_30d,
        max(case when o.ordered_at >= current_date - 90 then true else false end) as is_active_last_90d
    from o
    group by 1

),

-- ============================================================
-- Final assembly
-- ============================================================
final as (

    select
        -- ── Identity (4) ────────────────────────────────────────
        cb.customer_id,
        cb.customer_name,
        cb.customer_type,
        cb.customer_since_date,

        -- ── Order history (14) ──────────────────────────────────
        oh.first_order_date,
        oh.last_order_date,
        coalesce(oh.lifetime_orders, 0)                                     as lifetime_orders,
        coalesce(oh.lifetime_spend, 0)                                      as lifetime_spend,
        oh.avg_order_value,
        oh.max_order_value,
        oh.min_order_value,
        coalesce(id.total_items_purchased, 0)                               as total_items_purchased,
        case when coalesce(oh.lifetime_orders, 0) > 0
             then round(id.total_items_purchased::numeric / oh.lifetime_orders, 2)
             else 0
        end                                                                 as avg_items_per_order,
        coalesce(id.total_food_items, 0)                                    as total_food_items,
        coalesce(id.total_drink_items, 0)                                   as total_drink_items,
        case when coalesce(id.total_items_purchased, 0) > 0
             then round(id.total_food_items::numeric / id.total_items_purchased * 100, 2)
             else 0
        end                                                                 as pct_food_items,
        coalesce(oh.days_as_customer, 0)                                    as days_as_customer,
        case when coalesce(oh.days_as_customer, 0) > 0
             then round(oh.lifetime_orders::numeric / (oh.days_as_customer::numeric / 30), 2)
             else 0
        end                                                                 as orders_per_month,

        -- ── Recency / Frequency / Monetary (8) ─────────────────
        coalesce(oh.days_since_last_order, 0)                               as days_since_last_order,
        rfm.recency_score,
        rfm.frequency_score,
        rfm.monetary_score,
        rfm.rfm_segment,
        rfm.rfm_combined_score,
        coalesce(af.is_active_last_30d, false)                              as is_active_last_30d,
        coalesce(af.is_active_last_90d, false)                              as is_active_last_90d,

        -- ── Loyalty (12) ────────────────────────────────────────
        coalesce(loy.is_loyalty_member, false)                              as is_loyalty_member,
        loy.loyalty_member_id,
        loy.loyalty_join_date,
        coalesce(loy.loyalty_tenure_days, 0)                                as loyalty_tenure_days,
        loy.loyalty_tier,
        coalesce(loy.loyalty_points_balance, 0)                             as loyalty_points_balance,
        coalesce(lta.total_points_earned, 0)                                as total_points_earned,
        coalesce(lta.total_points_redeemed, 0)                              as total_points_redeemed,
        coalesce(lta.loyalty_transactions_count, 0)                         as loyalty_transactions_count,
        lta.avg_points_per_transaction,
        coalesce(lta.days_since_last_loyalty_activity, 0)                   as days_since_last_loyalty_activity,
        loy.loyalty_status,

        -- ── Preferences (12) ───────────────────────────────────
        sp.preferred_store_id,
        sp.preferred_store_name,
        coalesce(sv.stores_visited_count, 0)                                as stores_visited_count,
        dp.preferred_day_of_week,
        hp.preferred_hour_of_day,
        tp.top_product_1_id,
        tp.top_product_1_name,
        tp.top_product_2_id,
        tp.top_product_2_name,
        tp.top_product_3_id,
        tp.top_product_3_name,
        tp.preferred_product_type,

        -- ── Coupon behavior (8) ────────────────────────────────
        coalesce(cpb.has_used_coupon, false)                                as has_used_coupon,
        coalesce(cpb.total_coupons_used, 0)                                as total_coupons_used,
        coalesce(cpb.total_discount_received, 0)                            as total_discount_received,
        cpb.avg_discount_per_coupon,
        cpb.first_coupon_date,
        cpb.last_coupon_date,
        case when coalesce(cop.total_orders_for_pct, 0) > 0
             then round(cop.coupon_orders::numeric / cop.total_orders_for_pct * 100, 2)
             else 0
        end                                                                 as coupon_orders_pct,
        cpb.favorite_coupon_type_proxy,

        -- ── Engagement (6) ─────────────────────────────────────
        coalesce(rv.review_count, 0)                                        as review_count,
        rv.avg_review_score,
        acq.acquisition_source,
        coalesce(ee.email_engagement_proxy, 0)                              as email_engagement_proxy,

        -- ── Scoring (8) ────────────────────────────────────────
        cs.churn_propensity_score,
        cs.churn_risk_tier,
        ltv.lifetime_spend as ltv_lifetime_spend,
        ltv.ltv_tier,
        0 as customer_health_score,
        ltv.avg_order_value as ltv_avg_order_value,
        false as predicted_churn_flag,

        -- ── Trends (8) ─────────────────────────────────────────
        case when coalesce(st.avg_spend_prior_3m, 0) > 0
             then round(((st.avg_spend_recent_3m - st.avg_spend_prior_3m)
                        / st.avg_spend_prior_3m * 100), 2)
             else 0
        end                                                                 as spend_trend_3m,

        case when coalesce(st.avg_orders_prior_3m, 0) > 0
             then round(((st.avg_orders_recent_3m - st.avg_orders_prior_3m)
                        / st.avg_orders_prior_3m * 100), 2)
             else 0
        end                                                                 as order_frequency_trend_3m,

        case when coalesce(st.avg_aov_prior_3m, 0) > 0
             then round(((st.avg_aov_recent_3m - st.avg_aov_prior_3m)
                        / st.avg_aov_prior_3m * 100), 2)
             else 0
        end                                                                 as avg_order_value_trend_3m,

        coalesce(st.avg_spend_recent_3m, 0) > coalesce(st.avg_spend_prior_3m, 0)
                                                                            as is_spend_growing,
        coalesce(st.avg_orders_recent_3m, 0) > coalesce(st.avg_orders_prior_3m, 0)
                                                                            as is_frequency_growing,

        coalesce(st.months_of_declining_spend_raw, 0)                       as months_of_declining_spend,

        case when coalesce(oh.days_since_last_order, 999) > 90
                  and coalesce(af.is_active_last_30d, false)
             then true else false
        end                                                                 as reactivation_flag,

        case
            when oh.first_order_date is null                    then 'prospect'
            when oh.lifetime_orders = 1                         then 'new'
            when coalesce(oh.days_since_last_order, 999) <= 30  then 'active'
            when coalesce(oh.days_since_last_order, 999) <= 90  then 'cooling'
            when coalesce(oh.days_since_last_order, 999) <= 180 then 'at_risk'
            else 'churned'
        end                                                                 as lifecycle_stage

    from customer_base cb
    left join order_history oh              on cb.customer_id = oh.customer_id
    left join item_details id               on cb.customer_id = id.customer_id
    left join rfm                           on cb.customer_id = rfm.customer_id
    left join loyalty loy                   on cb.customer_id = loy.customer_id
    left join loyalty_txn_agg lta           on cb.customer_id = lta.customer_id
    left join store_preference sp           on cb.customer_id = sp.customer_id
    left join stores_visited sv             on cb.customer_id = sv.customer_id
    left join day_preference dp             on cb.customer_id = dp.customer_id
    left join hour_preference hp            on cb.customer_id = hp.customer_id
    left join top_products tp               on cb.customer_id = tp.customer_id
    left join coupon_behavior cpb           on cb.customer_id = cpb.customer_id
    left join coupon_order_pct cop          on cb.customer_id = cop.customer_id
    left join reviews rv                    on cb.customer_id = rv.customer_id
    left join acquisition acq              on cb.customer_id = acq.customer_id
    left join email_engagement ee           on cb.customer_id = ee.customer_id
    left join churn_score cs               on cb.customer_id = cs.customer_id
    left join ltv                           on cb.customer_id = ltv.customer_id
    left join spend_trends st              on cb.customer_id = st.customer_id
    left join active_flags af              on cb.customer_id = af.customer_id

)

select * from final
