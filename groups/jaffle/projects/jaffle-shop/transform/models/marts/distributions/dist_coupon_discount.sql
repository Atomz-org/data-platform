with

coupons as (
    select coupon_id, discount_applied from {{ ref('fct_coupon_redemptions') }}
),

stats as (
    select
        round(avg(discount_applied), 2) as mean_discount,
        round(percentile_cont(0.50) within group (order by discount_applied), 2) as median_discount,
        round(percentile_cont(0.75) within group (order by discount_applied), 2) as p75_discount,
        round(percentile_cont(0.90) within group (order by discount_applied), 2) as p90_discount
    from coupons
),

bucketed as (
    select
        case
            when discount_applied < 2 then '0-2'
            when discount_applied < 5 then '2-5'
            when discount_applied < 10 then '5-10'
            when discount_applied < 20 then '10-20'
            else '20+'
        end as discount_bucket,
        count(*) as redemption_count
    from coupons
    group by 1
)

select b.*, s.mean_discount, s.median_discount, s.p75_discount
from bucketed as b cross join stats as s
