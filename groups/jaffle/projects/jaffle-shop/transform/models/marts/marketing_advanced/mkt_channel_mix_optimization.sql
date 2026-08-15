with

cr as (
    select * from {{ ref('int_campaign_roi') }}
),

campaign_roi_by_type as (

    select
        cr.campaign_channel,
        count(*) as campaigns_count,
        sum(cr.total_spend) as total_spend,
        sum(cr.attributed_revenue) as total_revenue,
        avg(cr.roi_ratio * 100) as avg_roi_pct,
        case
            when sum(cr.total_spend) > 0
            then sum(cr.attributed_revenue) / sum(cr.total_spend)
            else 0
        end as overall_roas
    from cr
    group by 1

),

spend_daily as (

    select
        spend_channel as campaign_channel,
        sum(channel_spend) as total_daily_spend
    from {{ ref('int_marketing_spend_daily') }}
    group by 1

),

final as (

    select
        cr.campaign_channel,
        cr.campaigns_count,
        cr.total_spend,
        cr.total_revenue,
        cr.avg_roi_pct,
        cr.overall_roas,
        cast(cr.total_spend as {{ dbt.type_float() }})
            / nullif(sum(cr.total_spend) over (), 0) * 100 as current_spend_share_pct,
        -- Recommend: shift spend toward higher-ROAS campaign_channels
        case
            when cr.overall_roas > 3 then 'increase_investment'
            when cr.overall_roas > 1.5 then 'maintain_investment'
            when cr.overall_roas > 0 then 'optimize_or_reduce'
            else 'discontinue'
        end as investment_recommendation
    from campaign_roi_by_type as cr

)

select * from final
