with

redemptions as (

    select * from {{ ref('fct_coupon_redemptions') }}

),

coupons as (

    select * from {{ ref('dim_coupons') }}

),

customer_360 as (

    select * from {{ ref('dim_customer_360') }}

),

campaigns as (

    select * from {{ ref('dim_campaigns') }}

)

select
    r.redemption_id,
    r.coupon_id,
    cp.coupon_code,
    cp.discount_type,
    r.discount_applied,
    r.customer_id,
    c.customer_name,
    r.order_id,
    r.redeemed_at,
    cp.campaign_id,
    ca.campaign_name

from redemptions r
left join coupons cp on r.coupon_id = cp.coupon_id
left join customer_360 c on r.customer_id = c.customer_id
left join campaigns ca on cp.campaign_id = ca.campaign_id
