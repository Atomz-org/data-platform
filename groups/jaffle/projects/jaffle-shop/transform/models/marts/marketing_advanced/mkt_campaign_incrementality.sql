with

o as (
    select * from {{ ref('stg_orders') }}
),

campaign_roi as (

    select
        campaign_id,
        campaign_name,
        campaign_channel,
        first_spend_date,
        last_spend_date,
        attributed_revenue,
        total_spend,
        roi_ratio
    from {{ ref('int_campaign_roi') }}

),

-- Compare revenue during campaign vs equivalent period before
pre_campaign_revenue as (

    select
        c.campaign_id,
        sum(o.order_total) as pre_campaign_revenue,
        count(o.order_id) as pre_campaign_orders
    from campaign_roi as c
    inner join o
        on o.ordered_at >= {{ dbt.dateadd('day', '-30', 'c.first_spend_date') }}
        and o.ordered_at < c.first_spend_date
    group by 1

),

final as (

    select
        cr.campaign_id,
        cr.campaign_name,
        cr.campaign_channel,
        cr.attributed_revenue as campaign_period_revenue,
        coalesce(pcr.pre_campaign_revenue, 0) as pre_campaign_revenue,
        cr.attributed_revenue - coalesce(pcr.pre_campaign_revenue, 0) as incremental_revenue,
        cr.total_spend,
        case
            when cr.total_spend > 0
            then (cr.attributed_revenue - coalesce(pcr.pre_campaign_revenue, 0)) / cr.total_spend
            else null
        end as incremental_roi,
        case
            when cr.attributed_revenue > coalesce(pcr.pre_campaign_revenue, 0) * 1.1
            then 'positive_lift'
            when cr.attributed_revenue < coalesce(pcr.pre_campaign_revenue, 0) * 0.9
            then 'negative_lift'
            else 'no_significant_lift'
        end as incrementality_verdict
    from campaign_roi as cr
    left join pre_campaign_revenue as pcr on cr.campaign_id = pcr.campaign_id

)

select * from final
