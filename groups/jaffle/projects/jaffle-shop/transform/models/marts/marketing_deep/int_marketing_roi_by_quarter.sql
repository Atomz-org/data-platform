with

campaign_roi as (

    select * from {{ ref('int_campaign_roi') }}

),

marketing_spend as (

    select
        spend_date,
        sum(channel_spend) as daily_total_spend
    from {{ ref('int_marketing_spend_daily') }}
    group by 1

),

quarterly_roi as (

    select
        {{ dbt.date_trunc('quarter', 'first_spend_date') }} as roi_quarter,
        count(distinct campaign_id) as campaigns_count,
        sum(total_spend) as total_spend,
        sum(attributed_revenue) as total_attributed_revenue,
        case
            when sum(total_spend) > 0
                then round(cast(
                    (sum(attributed_revenue) - sum(total_spend)) * 100.0
                    / sum(total_spend)
                as {{ dbt.type_float() }}), 2)
            else 0
        end as quarterly_roi_pct,
        avg(roi_ratio * 100) as avg_campaign_roi_pct
    from campaign_roi
    group by 1

),

quarterly_spend as (

    select
        {{ dbt.date_trunc('quarter', 'spend_date') }} as spend_quarter,
        sum(daily_total_spend) as quarterly_marketing_spend
    from marketing_spend
    group by 1

),

final as (

    select
        qr.roi_quarter,
        qr.campaigns_count,
        qr.total_spend as campaign_direct_cost,
        coalesce(qs.quarterly_marketing_spend, 0) as total_marketing_spend,
        qr.total_attributed_revenue,
        qr.quarterly_roi_pct,
        qr.avg_campaign_roi_pct,
        case
            when coalesce(qs.quarterly_marketing_spend, 0) > 0
                then round(cast(
                    qr.total_attributed_revenue / qs.quarterly_marketing_spend
                as {{ dbt.type_float() }}), 2)
            else null
        end as revenue_per_marketing_dollar
    from quarterly_roi as qr
    left join quarterly_spend as qs
        on qr.roi_quarter = qs.spend_quarter

)

select * from final
