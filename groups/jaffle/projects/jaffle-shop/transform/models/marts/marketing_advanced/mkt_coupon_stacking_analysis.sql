with

redemptions as (

    select
        customer_id,
        order_id,
        coupon_id,
        discount_applied,
        redeemed_at
    from {{ ref('fct_coupon_redemptions') }}

),

coupons_per_order as (

    select
        order_id,
        customer_id,
        count(distinct coupon_id) as coupons_used,
        sum(discount_applied) as total_discount
    from redemptions
    group by 1, 2

),

order_values as (

    select
        order_id,
        order_total
    from {{ ref('stg_orders') }}

),

final as (

    select
        cpo.customer_id,
        cpo.order_id,
        cpo.coupons_used,
        cpo.total_discount,
        ov.order_total,
        case
            when ov.order_total > 0
            then cpo.total_discount / ov.order_total * 100
            else 0
        end as discount_pct_of_order,
        case
            when cpo.coupons_used > 1 then 'stacker'
            else 'single_coupon'
        end as stacking_behavior,
        case
            when cpo.coupons_used >= 3 then 'heavy_stacker'
            when cpo.coupons_used = 2 then 'moderate_stacker'
            else 'no_stacking'
        end as stacking_severity
    from coupons_per_order as cpo
    inner join order_values as ov on cpo.order_id = ov.order_id

)

select * from final
