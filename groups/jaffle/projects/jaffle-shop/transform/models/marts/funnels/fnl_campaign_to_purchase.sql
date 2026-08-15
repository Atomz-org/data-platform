with

campaigns as (

    select
        campaign_id,
        campaign_name,
        campaign_channel,
        campaign_start_date,
        campaign_end_date
    from {{ ref('dim_campaigns') }}

),

redemptions as (

    select
        campaign_id,
        coupon_id,
        customer_id,
        order_id,
        redeemed_at,
        discount_applied
    from {{ ref('fct_coupon_redemptions') }}
    where campaign_id is not null

),

orders as (

    select
        customer_id,
        order_id,
        ordered_at,
        order_total
    from {{ ref('stg_orders') }}

),

-- Stage 1: Campaigns launched (with coupons issued)
campaign_coupons as (

    select
        c.campaign_id,
        c.campaign_name,
        c.campaign_channel,
        count(distinct r.coupon_id) as coupons_associated,
        count(distinct r.customer_id) as customers_with_coupons
    from campaigns as c
    left join redemptions as r
        on c.campaign_id = r.campaign_id
    group by 1, 2, 3

),

-- Stage 2: Coupon redeemed
campaign_redemptions as (

    select
        campaign_id,
        count(distinct customer_id) as customers_redeemed,
        count(distinct order_id) as redemption_orders,
        sum(discount_applied) as total_discount
    from redemptions
    group by 1

),

-- Stage 3: Repeat purchase after redemption (within 90 days)
repeat_purchases as (

    select
        r.campaign_id,
        count(distinct r.customer_id) as customers_with_repeat
    from redemptions as r
    inner join orders as o
        on r.customer_id = o.customer_id
        and o.ordered_at > r.redeemed_at
        and {{ dbt.datediff('r.redeemed_at', 'o.ordered_at', 'day') }} <= 90
        and o.order_id != r.order_id
    group by 1

),

funnel as (

    select
        cc.campaign_id,
        cc.campaign_name,
        cc.campaign_channel,
        cc.customers_with_coupons as stage_1_coupon_recipients,
        coalesce(cr.customers_redeemed, 0) as stage_2_redeemed,
        coalesce(cr.redemption_orders, 0) as stage_2_orders,
        coalesce(rp.customers_with_repeat, 0) as stage_3_repeat_purchase,
        round(
            (coalesce(cr.customers_redeemed, 0) * 100.0
            / nullif(cc.customers_with_coupons, 0)), 2
        ) as redemption_rate_pct,
        round(
            (coalesce(rp.customers_with_repeat, 0) * 100.0
            / nullif(cr.customers_redeemed, 0)), 2
        ) as repeat_purchase_rate_pct
    from campaign_coupons as cc
    left join campaign_redemptions as cr
        on cc.campaign_id = cr.campaign_id
    left join repeat_purchases as rp
        on cc.campaign_id = rp.campaign_id

)

select * from funnel
