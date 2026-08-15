with

campaign_roi as (

    select * from {{ ref('int_campaign_roi') }}

),

reach_by_channel as (

    select * from {{ ref('int_campaign_reach_by_channel') }}

),

-- Aggregate ROI metrics by channel
channel_roi as (

    select
        campaign_channel,
        count(distinct campaign_id) as campaign_count,
        sum(total_spend) as total_spend,
        sum(attributed_revenue) as total_revenue,
        sum(attributed_orders) as total_orders,
        sum(attributed_customers) as total_customers,
        case
            when sum(total_spend) > 0
            then (sum(attributed_revenue) - sum(total_spend)) / sum(total_spend)
            else null
        end as channel_roi,
        case
            when sum(attributed_orders) > 0
            then sum(total_spend) / sum(attributed_orders)
            else null
        end as avg_cost_per_order

    from campaign_roi
    where campaign_channel is not null
    group by 1

),

-- Aggregate reach metrics by channel
channel_reach as (

    select
        spend_channel,
        sum(channel_spend) as reach_spend,
        sum(estimated_impressions) as total_estimated_impressions,
        sum(active_days) as total_active_days,
        avg(avg_daily_spend) as avg_daily_spend

    from reach_by_channel
    group by 1

),

-- Combine ROI and reach
final as (

    select
        channel_roi.campaign_channel,
        channel_roi.campaign_count,
        channel_roi.total_spend,
        channel_roi.total_revenue,
        channel_roi.total_orders,
        channel_roi.total_customers,
        channel_roi.channel_roi,
        channel_roi.avg_cost_per_order,
        coalesce(channel_reach.total_estimated_impressions, 0) as total_estimated_impressions,
        coalesce(channel_reach.total_active_days, 0) as total_active_days,
        channel_reach.avg_daily_spend,
        -- Conversion rate: orders per estimated impression
        case
            when coalesce(channel_reach.total_estimated_impressions, 0) > 0
            then channel_roi.total_orders * 1.0 / channel_reach.total_estimated_impressions
            else null
        end as estimated_conversion_rate,
        -- Revenue per impression
        case
            when coalesce(channel_reach.total_estimated_impressions, 0) > 0
            then channel_roi.total_revenue / channel_reach.total_estimated_impressions
            else null
        end as revenue_per_impression

    from channel_roi

    left join channel_reach
        on channel_roi.campaign_channel = channel_reach.spend_channel

)

select * from final
