with

coupon_redemptions as (

    select * from {{ ref('stg_coupon_redemptions') }}

),

coupons as (

    select * from {{ ref('stg_coupons') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

final as (

    select
        coupon_redemptions.redemption_id,
        coupon_redemptions.coupon_id,
        coupon_redemptions.order_id,
        coupon_redemptions.customer_id,
        coupon_redemptions.discount_applied,
        coupon_redemptions.redeemed_at,

        -- Coupon details
        coupons.coupon_code,
        coupons.discount_type,
        coupons.campaign_id,

        -- Order context
        orders.order_total,
        orders.subtotal,
        orders.ordered_at,

        -- Calculated fields
        case
            when orders.order_total > 0
            then coupon_redemptions.discount_applied / orders.order_total
            else null
        end as discount_pct_of_order,
        orders.order_total - coupon_redemptions.discount_applied as net_order_total

    from coupon_redemptions

    left join coupons
        on coupon_redemptions.coupon_id = coupons.coupon_id

    left join orders
        on coupon_redemptions.order_id = orders.order_id

)

select * from final
