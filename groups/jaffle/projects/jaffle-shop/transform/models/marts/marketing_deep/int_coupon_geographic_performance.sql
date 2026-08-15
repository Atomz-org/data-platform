with

redemptions as (

    select * from {{ ref('stg_coupon_redemptions') }}

),

orders as (

    select
        order_id,
        location_id
    from {{ ref('stg_orders') }}

),

locations as (

    select
        location_id,
        location_name
    from {{ ref('stg_locations') }}

),

coupons as (

    select
        coupon_id,
        coupon_code,
        discount_type,
        max_redemptions
    from {{ ref('stg_coupons') }}

),

final as (

    select
        l.location_id,
        l.location_name,
        c.discount_type,
        count(r.redemption_id) as total_redemptions,
        sum(r.discount_applied) as total_discount_given,
        avg(r.discount_applied) as avg_discount_per_redemption,
        count(distinct r.customer_id) as unique_customers_redeeming,
        count(distinct r.coupon_id) as distinct_coupons_used
    from redemptions as r
    inner join orders as o
        on r.order_id = o.order_id
    inner join locations as l
        on o.location_id = l.location_id
    inner join coupons as c
        on r.coupon_id = c.coupon_id
    group by 1, 2, 3

)

select * from final
