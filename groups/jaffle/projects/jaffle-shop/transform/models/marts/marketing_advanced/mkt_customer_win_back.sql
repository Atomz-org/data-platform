with

customer_360 as (

    select
        customer_id,
        rfm_segment_code as rfm_segment,
        days_since_last_order,
        total_orders,
        first_order_at,
        last_order_at
    from {{ ref('dim_customer_360') }}

),

coupon_activity as (

    select
        customer_id,
        min(redeemed_at) as first_coupon_after_lapse,
        count(*) as coupons_used
    from {{ ref('fct_coupon_redemptions') }}
    group by 1

),

orders_timeline as (

    select
        customer_id,
        ordered_at,
        lag(ordered_at) over (partition by customer_id order by ordered_at) as prev_order_date,
        {{ dbt.datediff(
            'lag(ordered_at) over (partition by customer_id order by ordered_at)',
            'ordered_at',
            'day'
        ) }} as days_between_orders
    from {{ ref('stg_orders') }}

),

lapsed_then_returned as (

    select
        customer_id,
        count(case when days_between_orders > 90 then 1 end) as lapse_count,
        max(days_between_orders) as max_gap_days
    from orders_timeline
    where days_between_orders is not null
    group by 1
    having count(case when days_between_orders > 90 then 1 end) > 0

),

final as (

    select
        c.customer_id,
        c.rfm_segment,
        c.total_orders,
        c.first_order_at,
        c.last_order_at,
        lr.lapse_count,
        lr.max_gap_days,
        ca.first_coupon_after_lapse,
        ca.coupons_used,
        case
            when ca.first_coupon_after_lapse is not null then 'coupon_triggered'
            else 'organic_return'
        end as win_back_trigger
    from lapsed_then_returned as lr
    inner join customer_360 as c on lr.customer_id = c.customer_id
    left join coupon_activity as ca on lr.customer_id = ca.customer_id

)

select * from final
