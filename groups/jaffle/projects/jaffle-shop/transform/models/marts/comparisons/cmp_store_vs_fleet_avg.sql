with

store_profile as (

    select * from {{ ref('dim_store_profile') }}

),

pnl as (

    select
        location_id,
        sum(monthly_revenue) as total_revenue,
        avg(net_profit_margin_pct) as avg_profit_margin_pct,
        avg(labor_cost_ratio_pct) as avg_labor_ratio_pct,
        avg(marketing_ratio_pct) as avg_marketing_ratio_pct
    from {{ ref('rpt_store_pnl') }}
    group by 1

),

fleet_avg as (

    select
        avg(total_revenue) as fleet_avg_revenue,
        avg(avg_operating_margin_pct) as fleet_avg_margin_pct,
        avg(avg_labor_cost_pct) as fleet_avg_labor_pct,
        avg(total_marketing_spend) as fleet_avg_marketing_spend,
        avg(avg_employee_count) as fleet_avg_employee_count
    from store_profile

),

comparison as (

    select
        sp.location_id,
        sp.store_name,

        -- Revenue
        sp.total_revenue as store_revenue,
        fa.fleet_avg_revenue,
        sp.total_revenue - fa.fleet_avg_revenue as revenue_vs_fleet,
        case
            when fa.fleet_avg_revenue > 0
            then round(((sp.total_revenue - fa.fleet_avg_revenue) / fa.fleet_avg_revenue * 100), 2)
            else 0
        end as revenue_vs_fleet_pct,

        -- Margin
        sp.avg_operating_margin_pct as store_margin_pct,
        fa.fleet_avg_margin_pct,
        sp.avg_operating_margin_pct - fa.fleet_avg_margin_pct as margin_vs_fleet_pp,

        -- Labor
        sp.avg_labor_cost_pct as store_labor_pct,
        fa.fleet_avg_labor_pct,
        sp.avg_labor_cost_pct - fa.fleet_avg_labor_pct as labor_vs_fleet_pp,

        -- Staffing
        sp.avg_employee_count as store_employees,
        fa.fleet_avg_employee_count,

        -- Ranking
        rank() over (order by sp.total_revenue desc) as revenue_rank,
        rank() over (order by sp.avg_operating_margin_pct desc) as margin_rank

    from store_profile as sp
    cross join fleet_avg as fa
    left join pnl
        on sp.location_id = pnl.location_id

)

select * from comparison
