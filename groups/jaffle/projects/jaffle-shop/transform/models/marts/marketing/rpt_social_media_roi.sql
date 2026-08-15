with

social_summary as (

    select * from {{ ref('int_social_engagement_summary') }}

),

campaign_roi as (

    select * from {{ ref('int_campaign_roi') }}

),

-- Get social campaign ROI data
social_campaign_roi as (

    select
        campaign_channel,
        sum(total_spend) as social_total_spend,
        sum(attributed_revenue) as social_attributed_revenue,
        sum(attributed_orders) as social_attributed_orders,
        sum(attributed_customers) as social_attributed_customers,
        case
            when sum(total_spend) > 0
            then (sum(attributed_revenue) - sum(total_spend)) / sum(total_spend)
            else null
        end as social_roi

    from campaign_roi
    where campaign_channel = 'social'
    group by 1

),

-- Combine social engagement metrics with revenue attribution
final as (

    select
        social_summary.platform,
        social_summary.total_posts,
        social_summary.total_impressions,
        social_summary.total_reach,
        social_summary.total_likes,
        social_summary.total_shares,
        social_summary.total_comments,
        social_summary.total_clicks,
        social_summary.total_engagements,
        social_summary.avg_engagement_rate,
        social_summary.avg_click_through_rate,
        -- Revenue attribution (from social campaigns overall)
        coalesce(social_campaign_roi.social_total_spend, 0) as social_campaign_spend,
        coalesce(social_campaign_roi.social_attributed_revenue, 0) as social_campaign_revenue,
        coalesce(social_campaign_roi.social_attributed_orders, 0) as social_campaign_orders,
        social_campaign_roi.social_roi,
        -- Cost per engagement (if spend data available)
        case
            when social_summary.total_engagements > 0
                and social_campaign_roi.social_total_spend is not null
            then social_campaign_roi.social_total_spend / social_summary.total_engagements
            else null
        end as cost_per_engagement,
        -- Revenue per click
        case
            when social_summary.total_clicks > 0
                and social_campaign_roi.social_attributed_revenue is not null
            then social_campaign_roi.social_attributed_revenue / social_summary.total_clicks
            else null
        end as revenue_per_click

    from social_summary

    -- Cross join since social_campaign_roi is a single-row aggregate for the 'social' channel
    left join social_campaign_roi
        on 1 = 1

)

select * from final
