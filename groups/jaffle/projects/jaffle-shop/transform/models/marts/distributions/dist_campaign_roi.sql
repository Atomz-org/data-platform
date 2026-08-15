with

campaigns as (
    select
        campaign_id,
        total_spend,
        budget,
        case when budget > 0 then round(total_spend / budget, 2) else null end as budget_utilization
    from {{ ref('fct_campaigns') }}
    where total_spend > 0
),

stats as (
    select
        count(*) as total_campaigns,
        round(avg(budget_utilization), 2) as mean_utilization,
        round(percentile_cont(0.50) within group (order by budget_utilization), 2) as median_utilization
    from campaigns
),

bucketed as (
    select
        case
            when budget_utilization < 0.5 then 'under_50pct'
            when budget_utilization < 1.0 then '50_to_100pct'
            when budget_utilization < 1.5 then '100_to_150pct'
            else 'over_150pct'
        end as utilization_bucket,
        count(*) as campaign_count,
        round(avg(budget_utilization), 2) as avg_utilization
    from campaigns
    group by 1
)

select b.*, s.mean_utilization, s.median_utilization, s.total_campaigns
from bucketed as b cross join stats as s
