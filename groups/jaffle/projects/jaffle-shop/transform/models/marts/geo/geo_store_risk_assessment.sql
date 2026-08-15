with

store_health as (

    select * from {{ ref('scr_store_health') }}

),

store_pnl as (

    select
        location_id,
        avg(net_profit_margin_pct) as avg_margin_pct,
        avg(labor_cost_ratio_pct) as avg_labor_ratio_pct,
        -- Recent revenue trend
        sum(case
            when report_month >= (select max(report_month) - interval '3 months' from {{ ref('rpt_store_pnl') }})
            then monthly_revenue else 0
        end) as recent_3m_revenue,
        sum(case
            when report_month >= (select max(report_month) - interval '6 months' from {{ ref('rpt_store_pnl') }})
                and report_month < (select max(report_month) - interval '3 months' from {{ ref('rpt_store_pnl') }})
            then monthly_revenue else 0
        end) as prior_3m_revenue

    from {{ ref('rpt_store_pnl') }}
    group by location_id

),

risk_flags as (

    select
        sh.location_id,
        sh.store_health_score,
        sp.avg_margin_pct,
        sp.avg_labor_ratio_pct,
        sp.recent_3m_revenue,
        sp.prior_3m_revenue,
        case when sp.recent_3m_revenue < sp.prior_3m_revenue * 0.9 then 1 else 0 end as declining_revenue_flag,
        case when sp.avg_labor_ratio_pct > 40 then 1 else 0 end as high_labor_cost_flag,
        case when sh.store_health_score < 50 then 1 else 0 end as low_health_score_flag,
        case when sp.avg_margin_pct < 5 then 1 else 0 end as low_margin_flag

    from store_health sh
    left join store_pnl sp on sh.location_id = sp.location_id

)

select
    location_id,
    round(store_health_score, 2) as store_health_score,
    round(avg_margin_pct, 2) as avg_margin_pct,
    round(avg_labor_ratio_pct, 2) as avg_labor_ratio_pct,
    declining_revenue_flag,
    high_labor_cost_flag,
    low_health_score_flag,
    low_margin_flag,
    declining_revenue_flag + high_labor_cost_flag + low_health_score_flag + low_margin_flag as total_risk_flags,
    case
        when declining_revenue_flag + high_labor_cost_flag + low_health_score_flag + low_margin_flag >= 3
        then 'critical_risk'
        when declining_revenue_flag + high_labor_cost_flag + low_health_score_flag + low_margin_flag >= 2
        then 'high_risk'
        when declining_revenue_flag + high_labor_cost_flag + low_health_score_flag + low_margin_flag >= 1
        then 'moderate_risk'
        else 'low_risk'
    end as risk_level

from risk_flags
