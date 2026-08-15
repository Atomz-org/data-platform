with

campaign_reach as (
    select
        campaign_id,
        campaign_name,
        active_spend_days,
        total_spend,
        channel_count
    from {{ ref('fct_campaigns') }}
),

ranked as (
    select
        campaign_id,
        campaign_name,
        active_spend_days as reach_proxy,
        total_spend,
        channel_count,
        rank() over (order by active_spend_days desc) as reach_rank,
        ntile(4) over (order by active_spend_days desc) as reach_quartile
    from campaign_reach
    where active_spend_days > 0
)

select * from ranked
