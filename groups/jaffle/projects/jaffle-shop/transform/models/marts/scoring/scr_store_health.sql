with

store_profile as (

    select * from {{ ref('dim_store_profile') }}

),

store_pnl as (

    select
        location_id,
        avg(net_profit_margin_pct) as avg_net_margin_pct,
        avg(labor_cost_ratio_pct) as avg_labor_ratio_pct,
        count(report_month) as months_of_pnl_data,
        -- Revenue growth: compare last 3 months to prior 3 months
        sum(case
            when report_month >= {{ dbt.date_trunc('month', dbt.current_timestamp()) }} - interval '3 months'
            then monthly_revenue else 0
        end) as recent_3m_revenue,
        sum(case
            when report_month >= {{ dbt.date_trunc('month', dbt.current_timestamp()) }} - interval '6 months'
                and report_month < {{ dbt.date_trunc('month', dbt.current_timestamp()) }} - interval '3 months'
            then monthly_revenue else 0
        end) as prior_3m_revenue

    from {{ ref('rpt_store_pnl') }}
    group by location_id

),

scored as (

    select
        sp.location_id,
        sp.store_name,
        sp.total_revenue,
        sp.avg_operating_margin_pct,
        sp.avg_labor_cost_pct,

        -- Revenue growth component (0-25)
        case
            when pnl.prior_3m_revenue > 0
                and (pnl.recent_3m_revenue - pnl.prior_3m_revenue) / pnl.prior_3m_revenue > 0.1 then 25
            when pnl.prior_3m_revenue > 0
                and (pnl.recent_3m_revenue - pnl.prior_3m_revenue) / pnl.prior_3m_revenue > 0 then 18
            when pnl.prior_3m_revenue > 0
                and (pnl.recent_3m_revenue - pnl.prior_3m_revenue) / pnl.prior_3m_revenue > -0.1 then 10
            else 5
        end as revenue_growth_score,

        -- Profitability component (0-25)
        case
            when coalesce(pnl.avg_net_margin_pct, 0) >= 15 then 25
            when coalesce(pnl.avg_net_margin_pct, 0) >= 10 then 20
            when coalesce(pnl.avg_net_margin_pct, 0) >= 5 then 15
            when coalesce(pnl.avg_net_margin_pct, 0) >= 0 then 8
            else 0
        end as profitability_score,

        -- Labor efficiency component (0-25): lower labor % = better
        case
            when coalesce(sp.avg_labor_cost_pct, 0) <= 20 then 25
            when coalesce(sp.avg_labor_cost_pct, 0) <= 30 then 20
            when coalesce(sp.avg_labor_cost_pct, 0) <= 40 then 12
            when coalesce(sp.avg_labor_cost_pct, 0) <= 50 then 5
            else 0
        end as labor_efficiency_score,

        -- Inventory health component (0-25): more products stocked = better
        case
            when coalesce(sp.distinct_products_stocked, 0) >= 20 then 25
            when coalesce(sp.distinct_products_stocked, 0) >= 15 then 20
            when coalesce(sp.distinct_products_stocked, 0) >= 10 then 15
            when coalesce(sp.distinct_products_stocked, 0) >= 5 then 8
            else 0
        end as inventory_health_score

    from store_profile as sp

    left join store_pnl as pnl
        on sp.location_id = pnl.location_id

),

final as (

    select
        location_id,
        store_name,
        total_revenue,
        avg_operating_margin_pct,
        avg_labor_cost_pct,
        revenue_growth_score,
        profitability_score,
        labor_efficiency_score,
        inventory_health_score,
        revenue_growth_score + profitability_score + labor_efficiency_score + inventory_health_score as store_health_score,
        case
            when revenue_growth_score + profitability_score + labor_efficiency_score + inventory_health_score >= 75 then 'excellent'
            when revenue_growth_score + profitability_score + labor_efficiency_score + inventory_health_score >= 50 then 'good'
            when revenue_growth_score + profitability_score + labor_efficiency_score + inventory_health_score >= 25 then 'needs_improvement'
            else 'critical'
        end as health_tier

    from scored

)

select * from final
