with 
c as (
    select * from {{ ref('stg_customers') }}
),

cr as (
    select * from {{ ref('stg_coupon_redemptions') }}
),

coupons as (
    select * from {{ ref('stg_coupons') }}
),

coupon_activity as (
    select
        cr.customer_id,
        count(distinct cr.redemption_id) as total_coupons_redeemed,
        count(distinct coupons.campaign_id) as campaigns_responded_to,
        min(cr.redeemed_at) as first_coupon_redeemed_at,
        max(cr.redeemed_at) as last_coupon_redeemed_at,
        sum(cr.discount_applied) as total_discount_received
    from cr
    left join coupons on cr.coupon_id = coupons.coupon_id
    group by cr.customer_id
),

acquisition as (
    select
        customer_id,
        acquisition_source,
        campaign_id as acquisition_campaign_id,
        acquired_at
    from {{ ref('int_customer_acquisition_source') }}
),

campaign_counts as (
    select
        count(distinct campaign_id) as total_campaigns_available
    from {{ ref('dim_campaigns') }}
)

select
    c.customer_id,
    coalesce(ca.total_coupons_redeemed, 0) as total_coupons_redeemed,
    coalesce(ca.campaigns_responded_to, 0) as campaigns_responded_to,
    round(
        (cast(coalesce(ca.campaigns_responded_to, 0) as {{ dbt.type_float() }})
        / nullif(cc.total_campaigns_available, 0) * 100), 2
    ) as campaign_response_rate_pct,
    coalesce(ca.total_discount_received, 0) as total_discount_received,
    ca.first_coupon_redeemed_at,
    ca.last_coupon_redeemed_at,
    acq.acquisition_source,
    acq.acquisition_campaign_id,
    acq.acquired_at as acquisition_date,
    case
        when ca.campaigns_responded_to >= 5 then 'highly_engaged'
        when ca.campaigns_responded_to >= 2 then 'moderately_engaged'
        when ca.campaigns_responded_to >= 1 then 'low_engagement'
        else 'no_engagement'
    end as marketing_engagement_level
from c
cross join campaign_counts as cc
left join coupon_activity as ca
    on c.customer_id = ca.customer_id
left join acquisition as acq
    on c.customer_id = acq.customer_id
