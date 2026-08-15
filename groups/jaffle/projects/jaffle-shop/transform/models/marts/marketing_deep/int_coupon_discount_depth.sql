with

redemptions as (

    select * from {{ ref('stg_coupon_redemptions') }}

),

coupons as (

    select
        coupon_id,
        coupon_code,
        discount_type,
        discount_amount,
        discount_percent
    from {{ ref('stg_coupons') }}

),

orders as (

    select
        order_id,
        order_total
    from {{ ref('stg_orders') }}

),

enriched as (

    select
        r.redemption_id,
        c.coupon_id,
        c.discount_type,
        r.discount_applied,
        o.order_total,
        case
            when o.order_total > 0
                then round(cast(r.discount_applied * 100.0 / o.order_total as {{ dbt.type_float() }}), 2)
            else 0
        end as effective_discount_pct
    from redemptions as r
    inner join coupons as c
        on r.coupon_id = c.coupon_id
    inner join orders as o
        on r.order_id = o.order_id

),

final as (

    select
        discount_type,
        count(redemption_id) as total_redemptions,
        avg(discount_applied) as avg_discount_amount,
        avg(effective_discount_pct) as avg_effective_discount_pct,
        min(effective_discount_pct) as min_effective_discount_pct,
        max(effective_discount_pct) as max_effective_discount_pct,
        avg(order_total) as avg_order_value_with_coupon
    from enriched
    group by 1

)

select * from final
