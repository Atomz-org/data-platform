with monthly_pnl as (
    select
        location_id,
        store_name,
        report_month,
        monthly_revenue,
        net_profit,
        net_profit_margin_pct
    from {{ ref('rpt_store_pnl') }}
),

revenue_growth as (
    select
        location_id,
        store_name,
        report_month,
        monthly_revenue,
        net_profit_margin_pct,
        lag(monthly_revenue) over (
            partition by location_id
            order by report_month
        ) as prev_month_revenue,
        case
            when lag(monthly_revenue) over (partition by location_id order by report_month) > 0
                then round(
                    (monthly_revenue - lag(monthly_revenue) over (partition by location_id order by report_month))
                    / lag(monthly_revenue) over (partition by location_id order by report_month) * 100, 2
                )
            else 0
        end as revenue_growth_pct
    from monthly_pnl
),

latest_period as (
    select
        location_id,
        store_name,
        monthly_revenue,
        net_profit_margin_pct,
        revenue_growth_pct,
        row_number() over (partition by location_id order by report_month desc) as rn
    from revenue_growth
    where prev_month_revenue is not null
),

medians as (
    select
        percentile_cont(0.5) within group (order by revenue_growth_pct) as median_growth,
        percentile_cont(0.5) within group (order by net_profit_margin_pct) as median_margin
    from latest_period
    where rn = 1
)

select
    lp.location_id,
    lp.store_name,
    lp.monthly_revenue as latest_revenue,
    lp.revenue_growth_pct,
    lp.net_profit_margin_pct,
    round(cast(m.median_growth as {{ dbt.type_float() }}), 2) as fleet_median_growth,
    round(cast(m.median_margin as {{ dbt.type_float() }}), 2) as fleet_median_margin,
    case
        when lp.revenue_growth_pct >= m.median_growth and lp.net_profit_margin_pct >= m.median_margin
            then 'Star'
        when lp.revenue_growth_pct < m.median_growth and lp.net_profit_margin_pct >= m.median_margin
            then 'Cash Cow'
        when lp.revenue_growth_pct >= m.median_growth and lp.net_profit_margin_pct < m.median_margin
            then 'Question Mark'
        else 'Dog'
    end as quadrant,
    case
        when lp.revenue_growth_pct >= m.median_growth and lp.net_profit_margin_pct >= m.median_margin
            then 'Invest for continued growth'
        when lp.revenue_growth_pct < m.median_growth and lp.net_profit_margin_pct >= m.median_margin
            then 'Maintain efficiency, explore growth levers'
        when lp.revenue_growth_pct >= m.median_growth and lp.net_profit_margin_pct < m.median_margin
            then 'Improve cost structure to capture growth value'
        else 'Review for turnaround or restructuring'
    end as strategic_recommendation
from latest_period as lp
cross join medians as m
where lp.rn = 1
