with

daily_spend as (

    select * from {{ ref('int_marketing_spend_daily') }}

),

reach_by_channel as (

    select * from {{ ref('int_campaign_reach_by_channel') }}

),

campaign_roi as (

    select * from {{ ref('int_campaign_roi') }}

),

-- Monthly spend by channel
monthly_spend as (

    select
        {{ dbt.date_trunc('month', 'spend_date') }} as month,
        spend_channel,
        sum(channel_spend) as monthly_channel_spend

    from daily_spend
    group by 1, 2

),

-- Monthly total for share calculation
monthly_totals as (

    select
        month,
        sum(monthly_channel_spend) as total_monthly_spend

    from monthly_spend
    group by 1

),

-- Channel-level reach totals
channel_reach as (

    select
        spend_channel,
        sum(estimated_impressions) as total_impressions,
        sum(channel_spend) as total_reach_spend

    from reach_by_channel
    group by 1

),

-- Channel-level ROI
channel_roi as (

    select
        campaign_channel,
        sum(attributed_revenue) as total_revenue,
        sum(attributed_orders) as total_orders,
        sum(total_spend) as total_campaign_spend,
        case
            when sum(total_spend) > 0
            then (sum(attributed_revenue) - sum(total_spend)) / sum(total_spend)
            else null
        end as channel_roi

    from campaign_roi
    where campaign_channel is not null
    group by 1

),

-- Combine into monthly channel mix
final as (

    select
        monthly_spend.month,
        monthly_spend.spend_channel,
        monthly_spend.monthly_channel_spend,
        monthly_totals.total_monthly_spend,
        -- Channel share of monthly spend
        case
            when monthly_totals.total_monthly_spend > 0
            then monthly_spend.monthly_channel_spend / monthly_totals.total_monthly_spend
            else null
        end as channel_spend_share,
        -- Overall channel metrics (not month-specific)
        coalesce(channel_reach.total_impressions, 0) as channel_total_impressions,
        coalesce(channel_roi.total_revenue, 0) as channel_total_revenue,
        coalesce(channel_roi.total_orders, 0) as channel_total_orders,
        channel_roi.channel_roi,
        -- Efficiency: revenue per spend dollar
        case
            when channel_roi.total_campaign_spend > 0
            then channel_roi.total_revenue / channel_roi.total_campaign_spend
            else null
        end as channel_revenue_per_dollar

    from monthly_spend

    inner join monthly_totals
        on monthly_spend.month = monthly_totals.month

    left join channel_reach
        on monthly_spend.spend_channel = channel_reach.spend_channel

    left join channel_roi
        on monthly_spend.spend_channel = channel_roi.campaign_channel

)

select * from final
order by month, spend_channel
