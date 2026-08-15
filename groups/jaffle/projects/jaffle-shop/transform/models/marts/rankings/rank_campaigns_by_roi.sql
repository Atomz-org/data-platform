with

campaign_roi as (
    select
        campaign_id,
        campaign_name,
        total_spend,
        budget,
        case when budget > 0 then round(total_spend / budget, 2) else null end as budget_utilization
    from {{ ref('fct_campaigns') }}
    where total_spend > 0
),

ranked as (
    select
        campaign_id,
        campaign_name,
        total_spend,
        budget,
        budget_utilization,
        rank() over (order by budget_utilization asc) as roi_rank,
        ntile(4) over (order by budget_utilization asc) as roi_quartile
    from campaign_roi
)

select * from ranked
