with

campaigns as (

    select * from {{ ref('stg_campaigns') }}

),

campaign_spend as (

    select * from {{ ref('stg_campaign_spend') }}

),

spend_summary as (

    select
        campaign_id,
        sum(spend_amount) as total_spend,
        count(distinct spend_channel) as channel_count,
        count(distinct spend_date) as active_spend_days,
        min(spend_date) as first_spend_date,
        max(spend_date) as last_spend_date

    from campaign_spend
    group by 1

),

final as (

    select
        campaigns.campaign_id,
        campaigns.campaign_name,
        campaigns.campaign_channel,
        campaigns.campaign_status,
        campaigns.campaign_description,
        campaigns.budget,
        campaigns.campaign_start_date,
        campaigns.campaign_end_date,
        campaigns.created_at,
        coalesce(spend_summary.total_spend, 0) as total_spend,
        spend_summary.channel_count,
        spend_summary.active_spend_days,
        spend_summary.first_spend_date,
        spend_summary.last_spend_date,
        case
            when campaigns.budget > 0
            then coalesce(spend_summary.total_spend, 0) / campaigns.budget
            else null
        end as budget_utilization

    from campaigns

    left join spend_summary
        on campaigns.campaign_id = spend_summary.campaign_id

)

select * from final
