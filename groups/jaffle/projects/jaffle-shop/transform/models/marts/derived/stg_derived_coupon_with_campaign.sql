with

coupons as (
    select * from {{ ref('stg_coupons') }}
),

campaigns as (
    select campaign_id, campaign_name, campaign_channel from {{ ref('stg_campaigns') }}
),

final as (
    select
        cp.coupon_id,
        cp.coupon_code,
        cp.discount_type,
        cp.discount_amount,
        cp.campaign_id,
        ca.campaign_name,
        ca.campaign_channel,
        cp.valid_from,
        cp.valid_until,
        cp.coupon_status
    from coupons as cp
    left join campaigns as ca on cp.campaign_id = ca.campaign_id
)

select * from final
