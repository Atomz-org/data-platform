with

campaign_conv as (
    select
        campaign_id,
        campaign_name,
        active_spend_days,
        total_spend,
        round(active_spend_days * 1.0 / nullif(total_spend, 0), 4) as efficiency
    from {{ ref('fct_campaigns') }}
    where total_spend > 0
),

ranked as (
    select
        campaign_id,
        campaign_name,
        active_spend_days,
        total_spend,
        efficiency,
        rank() over (order by efficiency desc) as conversion_rank,
        ntile(4) over (order by efficiency desc) as conversion_quartile
    from campaign_conv
)

select * from ranked
