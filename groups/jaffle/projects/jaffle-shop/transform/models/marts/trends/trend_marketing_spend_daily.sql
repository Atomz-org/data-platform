with

daily_spend as (
    select
        spend_date,
        spend_channel,
        sum(channel_spend) as total_spend
    from {{ ref('met_daily_marketing_spend') }}
    group by 1, 2
),

trended as (
    select
        spend_date,
        spend_channel,
        total_spend,
        avg(total_spend) over (
            partition by spend_channel order by spend_date
            rows between 6 preceding and current row
        ) as spend_7d_ma,
        avg(total_spend) over (
            partition by spend_channel order by spend_date
            rows between 27 preceding and current row
        ) as spend_28d_ma,
        sum(total_spend) over (
            partition by spend_channel order by spend_date
            rows between 27 preceding and current row
        ) as spend_28d_total,
        lag(total_spend, 7) over (partition by spend_channel order by spend_date) as spend_same_day_last_week
    from daily_spend
)

select * from trended
