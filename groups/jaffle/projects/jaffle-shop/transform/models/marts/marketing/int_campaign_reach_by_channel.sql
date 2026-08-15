with

campaigns as (

    select * from {{ ref('fct_campaigns') }}

),

campaign_spend as (

    select * from {{ ref('stg_campaign_spend') }}

),

-- Aggregate spend by campaign and channel
spend_by_channel as (

    select
        campaign_spend.campaign_id,
        campaign_spend.spend_channel,
        sum(campaign_spend.spend_amount) as channel_spend,
        count(distinct campaign_spend.spend_date) as active_days,
        min(campaign_spend.spend_date) as first_spend_date,
        max(campaign_spend.spend_date) as last_spend_date

    from campaign_spend
    group by 1, 2

),

-- Join with campaign details and estimate reach from spend
final as (

    select
        spend_by_channel.campaign_id,
        campaigns.campaign_name,
        spend_by_channel.spend_channel,
        spend_by_channel.channel_spend,
        spend_by_channel.active_days,
        spend_by_channel.first_spend_date,
        spend_by_channel.last_spend_date,
        campaigns.total_spend as campaign_total_spend,
        -- Channel share of total campaign spend
        case
            when campaigns.total_spend > 0
            then spend_by_channel.channel_spend / campaigns.total_spend
            else null
        end as channel_spend_share,
        -- Estimated impressions based on channel spend (rough CPM proxy)
        case
            when spend_by_channel.spend_channel = 'email' then spend_by_channel.channel_spend * 500
            when spend_by_channel.spend_channel = 'social' then spend_by_channel.channel_spend * 300
            when spend_by_channel.spend_channel = 'in-store' then spend_by_channel.channel_spend * 100
            else spend_by_channel.channel_spend * 200
        end as estimated_impressions,
        -- Average daily spend in channel
        case
            when spend_by_channel.active_days > 0
            then spend_by_channel.channel_spend / spend_by_channel.active_days
            else null
        end as avg_daily_spend

    from spend_by_channel

    inner join campaigns
        on spend_by_channel.campaign_id = campaigns.campaign_id

)

select * from final
