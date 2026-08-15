with

campaigns as (

    select * from {{ ref('stg_campaigns') }}

),

coupon_redemptions as (

    select * from {{ ref('stg_coupon_redemptions') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

coupons as (

    select * from {{ ref('stg_coupons') }}

),

-- Link campaigns to orders through coupons and their redemptions
campaign_coupons as (

    select
        coupons.campaign_id,
        coupons.coupon_id
    from coupons
    where coupons.campaign_id is not null

),

attributed_orders as (

    select
        campaigns.campaign_id,
        campaigns.campaign_name,
        campaigns.campaign_channel,
        orders.order_id,
        orders.customer_id,
        orders.order_total,
        orders.subtotal,
        coupon_redemptions.redemption_id,
        coupon_redemptions.discount_applied,
        orders.ordered_at

    from coupon_redemptions

    inner join campaign_coupons
        on coupon_redemptions.coupon_id = campaign_coupons.coupon_id

    inner join campaigns
        on campaign_coupons.campaign_id = campaigns.campaign_id

    inner join orders
        on coupon_redemptions.order_id = orders.order_id

)

select * from attributed_orders
