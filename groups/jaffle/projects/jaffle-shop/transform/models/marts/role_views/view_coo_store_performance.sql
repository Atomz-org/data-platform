with

store_profile as (

    select * from {{ ref('dim_store_profile') }}

),

store_health as (

    select * from {{ ref('scr_store_health') }}

)

select
    sp.location_id,
    sp.store_name,
    sh.store_health_score,
    sh.revenue_growth_score,
    sh.profitability_score,
    sh.labor_efficiency_score,
    rank() over (order by sh.store_health_score desc) as performance_rank,
    case
        when sh.store_health_score >= 80 then 'top_performer'
        when sh.store_health_score >= 60 then 'solid_performer'
        when sh.store_health_score >= 40 then 'average'
        else 'underperformer'
    end as performance_tier

from store_profile sp
left join store_health sh on sp.location_id = sh.location_id
