with

store_health as (

    select * from {{ ref('scr_store_health') }}

),

store_profile as (

    select * from {{ ref('dim_store_profile') }}

),

store_pnl as (

    select
        location_id,
        report_month,
        monthly_revenue,
        net_profit_margin_pct,
        labor_cost_ratio_pct
    from {{ ref('rpt_store_pnl') }}

),

latest_pnl as (

    select
        location_id,
        monthly_revenue as latest_monthly_revenue,
        net_profit_margin_pct as latest_profit_margin,
        labor_cost_ratio_pct as latest_labor_ratio,
        row_number() over (partition by location_id order by report_month desc) as rn
    from store_pnl

),

final as (

    select
        sp.location_id,
        sp.store_name,
        sp.total_revenue,
        sp.avg_operating_margin_pct,
        sp.avg_labor_cost_pct,
        sp.months_of_data,
        sh.store_health_score,
        sh.health_tier,
        lp.latest_monthly_revenue,
        lp.latest_profit_margin,
        lp.latest_labor_ratio
    from store_profile as sp
    left join store_health as sh
        on sp.location_id = sh.location_id
    left join latest_pnl as lp
        on sp.location_id = lp.location_id
        and lp.rn = 1

)

select * from final
