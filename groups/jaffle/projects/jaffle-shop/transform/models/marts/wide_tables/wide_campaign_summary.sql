with

campaigns as (

    select * from {{ ref('dim_campaigns') }}

),

campaign_effectiveness as (

    select * from {{ ref('rpt_campaign_effectiveness') }}

),

campaign_roi as (

    select * from {{ ref('int_campaign_roi') }}

)

select
    c.campaign_id,
    c.campaign_name,
    c.campaign_channel,
    c.campaign_start_date,
    c.campaign_end_date,
    c.budget,
    ce.total_spend,
    ce.attributed_revenue,
    ce.attributed_orders,
    round(ce.roi_ratio * 100, 2) as roi_pct,
    ce.cost_per_order,
    cr.attributed_revenue as roi_attributed_revenue,
    case
        when round(ce.roi_ratio * 100, 2) >= 200 then 'top_performer'
        when round(ce.roi_ratio * 100, 2) >= 100 then 'profitable'
        when round(ce.roi_ratio * 100, 2) >= 0 then 'break_even'
        else 'loss'
    end as campaign_performance_tier

from campaigns c
left join campaign_effectiveness ce on c.campaign_id = ce.campaign_id
left join campaign_roi cr on c.campaign_id = cr.campaign_id
