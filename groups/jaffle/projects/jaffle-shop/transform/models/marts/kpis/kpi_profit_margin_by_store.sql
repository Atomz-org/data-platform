with 
r as (
    select * from {{ ref('met_monthly_revenue_by_store') }}
),

w as (
    select * from {{ ref('met_monthly_waste_metrics') }}
),

l as (
    select * from {{ ref('met_monthly_labor_metrics') }}
),

store_financials as (
    select
        r.month_start,
        r.location_id,
        r.monthly_revenue,
        coalesce(l.monthly_labor_cost, 0) as labor_cost,
        coalesce(w.monthly_waste_cost, 0) as waste_cost,
        r.monthly_revenue - coalesce(l.monthly_labor_cost, 0) - coalesce(w.monthly_waste_cost, 0) as operating_profit
    from r
    left join l
        on r.month_start = l.month_start and r.location_id = l.location_id
    left join w
        on r.month_start = w.month_start and r.location_id = w.location_id
),
final as (
    select
        month_start,
        location_id,
        monthly_revenue,
        operating_profit,
        round(operating_profit * 100.0 / nullif(monthly_revenue, 0), 2) as profit_margin_pct
    from store_financials
)
select * from final
