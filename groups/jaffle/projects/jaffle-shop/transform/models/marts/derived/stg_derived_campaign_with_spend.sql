with

campaigns as (
    select * from {{ ref('stg_campaigns') }}
),

spend as (
    select campaign_id, sum(spend_amount) as total_spend
    from {{ ref('stg_campaign_spend') }}
    group by 1
),

final as (
    select
        c.campaign_id,
        c.campaign_name,
        c.campaign_channel,
        c.campaign_start_date,
        c.campaign_end_date,
        c.campaign_status,
        coalesce(s.total_spend, 0) as total_spend
    from campaigns as c
    left join spend as s on c.campaign_id = s.campaign_id
)

select * from final
