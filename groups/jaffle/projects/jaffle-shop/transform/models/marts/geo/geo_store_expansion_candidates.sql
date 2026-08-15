with

store_health as (
    select * from {{ ref('scr_store_health') }}
),

store_profile as (
    select * from {{ ref('dim_store_profile') }}
),

high_performers as (
    select
        sh.location_id,
        sp.store_name,
        sh.store_health_score,
        sh.revenue_growth_score,
        sh.profitability_score
    from store_health sh
    inner join store_profile sp on sh.location_id = sp.location_id
    where sh.store_health_score >= 70
)

select
    location_id,
    store_name,
    store_health_score,
    revenue_growth_score,
    profitability_score,
    case
        when store_health_score >= 85 and revenue_growth_score >= 80
        then 'strong_expansion_candidate'
        when store_health_score >= 70 and revenue_growth_score >= 60
        then 'moderate_expansion_candidate'
        else 'monitor'
    end as expansion_recommendation
from high_performers
