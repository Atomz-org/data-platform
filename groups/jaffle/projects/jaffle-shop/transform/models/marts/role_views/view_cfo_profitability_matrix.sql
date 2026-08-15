with

store_pnl as (

    select * from {{ ref('rpt_store_pnl') }}

),

latest_month as (

    select max(report_month) as max_month from store_pnl

),

recent_pnl as (

    select
        location_id,
        avg(monthly_revenue) as avg_revenue,
        avg(net_profit_margin_pct) as avg_margin_pct,
        avg(net_profit_margin_pct) as avg_net_profit_margin_pct,
        sum(monthly_revenue) as total_revenue,
        sum(net_profit) as total_net_profit

    from store_pnl
    where report_month >= (select max_month - interval '6 months' from latest_month)
    group by location_id

)

select
    location_id,
    round(avg_revenue, 2) as avg_monthly_revenue,
    round(avg_margin_pct, 2) as avg_net_margin_pct,
    round(avg_net_profit_margin_pct, 2) as avg_net_profit_margin_pct,
    round(total_revenue, 2) as six_month_revenue,
    round(total_net_profit, 2) as six_month_net_profit,
    rank() over (order by avg_margin_pct desc) as margin_rank,
    rank() over (order by avg_revenue desc) as revenue_rank,
    case
        when avg_margin_pct >= 15 then 'high_margin'
        when avg_margin_pct >= 5 then 'moderate_margin'
        else 'low_margin'
    end as margin_category

from recent_pnl
