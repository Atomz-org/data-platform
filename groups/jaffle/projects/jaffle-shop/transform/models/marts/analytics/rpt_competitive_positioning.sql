with

store_profile as (

    select * from {{ ref('dim_store_profile') }}

),

store_health as (

    select
        location_id,
        store_health_score,
        health_tier
    from {{ ref('scr_store_health') }}

),

store_revenue as (

    select
        location_id,
        sum(monthly_revenue) as total_revenue,
        avg(monthly_revenue) as avg_monthly_revenue,
        count(distinct month_start) as months_active
    from {{ ref('met_monthly_revenue_by_store') }}
    group by 1

),

benchmarks as (

    select
        avg(sr.avg_monthly_revenue) as company_avg_monthly_revenue,
        avg(sp.avg_operating_margin_pct) as company_avg_margin,
        avg(sh.store_health_score) as company_avg_store_health_score
    from store_revenue as sr
    inner join store_profile as sp
        on sr.location_id = sp.location_id
    left join store_health as sh
        on sr.location_id = sh.location_id

),

final as (

    select
        sp.location_id,
        sp.store_name,
        sr.avg_monthly_revenue,
        sp.avg_operating_margin_pct,
        sh.store_health_score,
        b.company_avg_monthly_revenue,
        b.company_avg_margin,
        case
            when b.company_avg_monthly_revenue > 0
                then round(cast(sr.avg_monthly_revenue / b.company_avg_monthly_revenue as {{ dbt.type_float() }}), 2)
            else null
        end as revenue_index_vs_company,
        case
            when sr.avg_monthly_revenue > b.company_avg_monthly_revenue
                and sp.avg_operating_margin_pct > b.company_avg_margin
                then 'leader'
            when sr.avg_monthly_revenue > b.company_avg_monthly_revenue
                then 'revenue_strong'
            when sp.avg_operating_margin_pct > b.company_avg_margin
                then 'margin_strong'
            else 'lagging'
        end as competitive_position
    from store_profile as sp
    inner join store_revenue as sr
        on sp.location_id = sr.location_id
    left join store_health as sh
        on sp.location_id = sh.location_id
    cross join benchmarks as b

)

select * from final
