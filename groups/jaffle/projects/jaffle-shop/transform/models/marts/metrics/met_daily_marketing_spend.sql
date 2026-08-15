with

marketing as (

    select * from {{ ref('int_marketing_spend_daily') }}

),

daily_totals as (

    select
        spend_date,
        spend_channel,
        channel_spend,
        campaigns_active,
        total_daily_spend,
        total_campaigns_active,
        channels_active,
        channel_daily_share,
        channel_spend_7d_avg,

        -- 7-day rolling avg of total daily spend
        avg(total_daily_spend) over (
            order by spend_date
            rows between 6 preceding and current row
        ) as total_spend_7d_avg

    from marketing

)

select * from daily_totals
