with

store_profile as (

    select * from {{ ref('dim_store_profile') }}

),

store_pnl as (

    select
        location_id,
        sum(monthly_revenue) as total_revenue,
        sum(net_profit) as total_net_profit,
        avg(net_profit_margin_pct) as avg_net_margin_pct,
        avg(labor_cost_ratio_pct) as avg_labor_ratio_pct,
        count(distinct report_month) as months_of_data
    from {{ ref('rpt_store_pnl') }}
    group by location_id

),

-- Since stores may not have a region field, group by store
store_summary as (

    select
        sp.location_id,
        sp.store_name,
        sp.total_revenue as profile_total_revenue,
        sp.avg_operating_margin_pct,
        sp.avg_labor_cost_pct,
        sp.avg_employee_count,
        coalesce(pnl.total_revenue, 0) as pnl_total_revenue,
        coalesce(pnl.total_net_profit, 0) as total_net_profit,
        coalesce(pnl.avg_net_margin_pct, 0) as avg_net_margin_pct,
        coalesce(pnl.avg_labor_ratio_pct, 0) as pnl_avg_labor_ratio_pct,
        coalesce(pnl.months_of_data, 0) as months_of_data,

        -- Revenue growth: recent vs prior half of available data
        case
            when coalesce(pnl.total_revenue, 0) > 0
            then round(cast(coalesce(pnl.total_net_profit, 0) * 100.0 / pnl.total_revenue as {{ dbt.type_float() }}), 2)
            else 0
        end as net_profit_margin_pct

    from store_profile as sp

    left join store_pnl as pnl
        on sp.location_id = pnl.location_id

)

select * from store_summary
