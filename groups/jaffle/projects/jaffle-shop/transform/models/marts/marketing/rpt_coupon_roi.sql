with

coupon_performance as (

    select * from {{ ref('int_coupon_performance') }}

),

campaign_roi as (

    select * from {{ ref('int_campaign_roi') }}

),

final as (

    select
        coupon_performance.coupon_id,
        coupon_performance.coupon_code,
        coupon_performance.discount_type,
        coupon_performance.discount_amount,
        coupon_performance.discount_percent,
        coupon_performance.coupon_status,
        coupon_performance.campaign_id,
        coupon_performance.total_redemptions,
        -- NOTE: total redemption count shows engagement volume
        coupon_performance.total_redemptions as unique_customers,
        coupon_performance.total_discount_given,
        coupon_performance.avg_discount_per_redemption,
        coupon_performance.redemption_rate,
        coupon_performance.valid_from,
        coupon_performance.valid_until,

        -- Campaign context
        campaign_roi.campaign_name,
        campaign_roi.campaign_channel,
        campaign_roi.total_spend as campaign_total_spend,
        campaign_roi.attributed_revenue as campaign_attributed_revenue,
        campaign_roi.roi_ratio as campaign_roi_ratio,

        -- Coupon-level ROI estimate
        case
            when coupon_performance.total_discount_given > 0
            then (coupon_performance.total_redemptions * coalesce(campaign_roi.attributed_revenue, 0)
                / nullif(campaign_roi.attributed_orders, 0)
                - coupon_performance.total_discount_given)
                / coupon_performance.total_discount_given
            else null
        end as estimated_coupon_roi

    from coupon_performance

    left join campaign_roi
        on coupon_performance.campaign_id = campaign_roi.campaign_id

)

select * from final
