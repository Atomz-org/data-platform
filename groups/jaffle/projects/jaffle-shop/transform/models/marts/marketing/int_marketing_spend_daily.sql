with

campaign_spend as (

    select * from {{ ref('stg_campaign_spend') }}

),

-- Daily spend by channel
daily_channel_spend as (

    select
        spend_date,
        spend_channel,
        sum(spend_amount) as channel_spend,
        count(distinct campaign_id) as campaigns_active

    from campaign_spend
    group by 1, 2

),

-- Daily total across all channels
daily_total as (

    select
        spend_date,
        sum(channel_spend) as total_daily_spend,
        sum(campaigns_active) as total_campaigns_active,
        count(distinct spend_channel) as channels_active

    from daily_channel_spend
    group by 1

),

-- Combine channel-level and total for daily summary
final as (

    select
        daily_channel_spend.spend_date,
        daily_channel_spend.spend_channel,
        daily_channel_spend.channel_spend,
        daily_channel_spend.campaigns_active,
        daily_total.total_daily_spend,
        daily_total.total_campaigns_active,
        daily_total.channels_active,
        -- Channel share of daily spend
        case
            when daily_total.total_daily_spend > 0
            then daily_channel_spend.channel_spend / daily_total.total_daily_spend
            else null
        end as channel_daily_share,
        -- 7-day rolling average of channel spend
        avg(daily_channel_spend.channel_spend) over (
            partition by daily_channel_spend.spend_channel
            order by daily_channel_spend.spend_date
            rows between 6 preceding and current row
        ) as channel_spend_7d_avg

    from daily_channel_spend

    inner join daily_total
        on daily_channel_spend.spend_date = daily_total.spend_date

)

select * from final
