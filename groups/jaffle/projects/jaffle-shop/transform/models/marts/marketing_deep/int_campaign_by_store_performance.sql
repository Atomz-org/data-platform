with

redemptions as (

    select * from {{ ref('stg_coupon_redemptions') }}

),

orders as (

    select
        order_id,
        location_id,
        order_total
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
        campaign_id
    from {{ ref('stg_coupons') }}

),

campaigns as (

    select
        campaign_id,
        campaign_name
    from {{ ref('stg_campaigns') }}

),

redemption_by_store as (

    select
        camp.campaign_id,
        camp.campaign_name,
        o.location_id,
        l.location_name,
        count(r.redemption_id) as redemption_count,
        sum(r.discount_applied) as total_discount,
        sum(o.order_total) as total_order_revenue,
        avg(o.order_total) as avg_order_value
    from redemptions as r
    inner join coupons as c
        on r.coupon_id = c.coupon_id
    inner join campaigns as camp
        on c.campaign_id = camp.campaign_id
    inner join orders as o
        on r.order_id = o.order_id
    left join locations as l
        on o.location_id = l.location_id
    group by 1, 2, 3, 4

)

select * from redemption_by_store
