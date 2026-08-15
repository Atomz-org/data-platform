with

store_profile as (

    select * from {{ ref('dim_store_profile') }}

),

store_pnl as (

    select
        location_id,
        avg(monthly_revenue) as avg_monthly_revenue,
        avg(net_profit_margin_pct) as avg_margin_pct

    from {{ ref('rpt_store_pnl') }}
    group by location_id

),

revenue_stats as (

    select
        percentile_cont(0.33) within group (order by avg_monthly_revenue) as rev_low,
        percentile_cont(0.66) within group (order by avg_monthly_revenue) as rev_high,
        percentile_cont(0.33) within group (order by avg_margin_pct) as margin_low,
        percentile_cont(0.66) within group (order by avg_margin_pct) as margin_high

    from store_pnl

),

clustered as (

    select
        sp.location_id,
        dp.store_name,
        sp.avg_monthly_revenue,
        sp.avg_margin_pct,
        case
            when sp.avg_monthly_revenue >= rs.rev_high then 'high_revenue'
            when sp.avg_monthly_revenue >= rs.rev_low then 'mid_revenue'
            else 'low_revenue'
        end as revenue_tier,
        case
            when sp.avg_margin_pct >= rs.margin_high then 'high_margin'
            when sp.avg_margin_pct >= rs.margin_low then 'mid_margin'
            else 'low_margin'
        end as margin_tier

    from store_pnl sp
    cross join revenue_stats rs
    left join store_profile dp on sp.location_id = dp.location_id

)

select
    location_id,
    store_name,
    round(avg_monthly_revenue, 2) as avg_monthly_revenue,
    round(avg_margin_pct, 2) as avg_margin_pct,
    revenue_tier,
    margin_tier,
    revenue_tier || '_' || margin_tier as cluster_label,
    case
        when revenue_tier = 'high_revenue' and margin_tier = 'high_margin' then 'star_performer'
        when revenue_tier = 'high_revenue' and margin_tier = 'low_margin' then 'revenue_driver'
        when revenue_tier = 'low_revenue' and margin_tier = 'high_margin' then 'niche_profitable'
        when revenue_tier = 'low_revenue' and margin_tier = 'low_margin' then 'underperformer'
        else 'middle_pack'
    end as cluster_description

from clustered
