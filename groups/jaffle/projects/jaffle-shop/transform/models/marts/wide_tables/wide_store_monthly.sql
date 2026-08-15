with

orders_base as (
    select * from {{ ref('orders') }}
),

order_items_base as (
    select * from {{ ref('order_items') }}
),

monthly_revenue as (

    select * from {{ ref('met_monthly_revenue_by_store') }}

),

monthly_labor as (

    select * from {{ ref('met_monthly_labor_metrics') }}

),

monthly_customers as (

    select * from {{ ref('met_monthly_customer_metrics') }}

),

store_pnl as (

    select * from {{ ref('rpt_store_pnl') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

store_health as (

    select * from {{ ref('scr_store_health') }}

),

monthly_waste as (

    select * from {{ ref('met_monthly_waste_metrics') }}

),

monthly_inventory as (

    select * from {{ ref('met_monthly_inventory_metrics') }}

),

monthly_marketing as (

    select * from {{ ref('met_monthly_marketing_metrics') }}

),

monthly_product_sales as (

    select * from {{ ref('met_monthly_product_sales') }}

),

-- Order-level product mix per store per month
product_mix as (

    select
        o.location_id,
        {{ dbt.date_trunc('month', 'o.ordered_at') }} as order_month,
        sum(case when oi.is_food_item then oi.product_price else 0 end) as food_revenue,
        sum(case when oi.is_drink_item then oi.product_price else 0 end) as beverage_revenue,
        count(distinct oi.product_id) as unique_products_sold,
        count(distinct o.order_id) as total_orders_with_items

    from orders_base as o
    inner join order_items_base as oi
        on o.order_id = oi.order_id
    group by 1, 2

),

-- New vs returning customers per store per month
customer_segments as (

    select
        o.location_id,
        {{ dbt.date_trunc('month', 'o.ordered_at') }} as order_month,
        count(distinct o.customer_id) as unique_customers,
        count(distinct case when o.customer_order_number = 1 then o.customer_id end) as new_customers,
        count(distinct case when o.customer_order_number > 1 then o.customer_id end) as returning_customers

    from orders_base as o
    group by 1, 2

)

select
    -- Store info
    mr.location_id,
    coalesce(l.location_name, mr.store_name) as location_name,
    l.opened_date,
    {{ dbt.datediff("l.opened_date", "mr.month_start", "month") }} as store_age_months,
    l.tax_rate as store_tax_rate,

    -- Time dimensions
    mr.month_start,
    mr.month_start + interval '1 month' - interval '1 day' as month_end,
    mr.fiscal_month,
    mr.fiscal_quarter,
    mr.fiscal_year,
    extract(month from mr.month_start) as calendar_month,
    extract(quarter from mr.month_start) as calendar_quarter,
    extract(year from mr.month_start) as calendar_year,

    -- Revenue
    mr.monthly_revenue as total_revenue,
    mr.monthly_orders as total_orders,
    mr.avg_order_value,
    mr.monthly_gross_revenue as gross_revenue,
    mr.monthly_tax_collected as tax_collected,
    case
        when mr.active_days > 0
        then mr.monthly_revenue * 1.0 / mr.active_days
        else 0
    end as revenue_per_day,
    mr.mom_revenue_growth as revenue_growth_mom,
    mr.yoy_revenue_growth as revenue_growth_yoy,
    mr.prev_month_revenue,
    mr.same_month_last_year_revenue,
    mr.active_days,

    -- Product mix
    coalesce(pm.food_revenue, 0) as food_revenue,
    coalesce(pm.beverage_revenue, 0) as beverage_revenue,
    case
        when mr.monthly_revenue > 0
        then coalesce(pm.food_revenue, 0) * 100.0 / mr.monthly_revenue
        else 0
    end as food_pct,
    case
        when mr.monthly_revenue > 0
        then coalesce(pm.beverage_revenue, 0) * 100.0 / mr.monthly_revenue
        else 0
    end as beverage_pct,
    coalesce(pm.unique_products_sold, 0) as unique_products_sold,

    -- Customer metrics
    coalesce(cs.unique_customers, 0) as unique_customers,
    coalesce(cs.new_customers, 0) as new_customers,
    coalesce(cs.returning_customers, 0) as returning_customers,
    case
        when coalesce(cs.unique_customers, 0) > 0
        then cs.new_customers * 100.0 / cs.unique_customers
        else 0
    end as new_customer_pct,
    case
        when coalesce(cs.unique_customers, 0) > 0
        then mr.monthly_revenue * 1.0 / cs.unique_customers
        else 0
    end as avg_customer_spend,
    case
        when coalesce(cs.unique_customers, 0) > 0
        then cs.returning_customers * 100.0 / cs.unique_customers
        else 0
    end as customer_retention_rate,
    mc.new_customers as mc_new_customers,
    mc.returning_customer_visits,
    mc.tracked_active_customers as mc_active_customers,
    mc.dormant_customers,
    mc.churned_customers,
    mc.active_pct as customer_active_pct,
    mc.churn_pct as customer_churn_pct,

    -- Labor
    coalesce(ml.monthly_labor_hours, 0) as total_labor_hours,
    coalesce(ml.monthly_labor_cost, 0) as total_labor_cost,
    ml.labor_cost_pct_of_revenue as labor_cost_pct,
    ml.avg_daily_employees,
    ml.orders_per_labor_hour,
    ml.mom_labor_cost_change,
    ml.prev_month_labor_cost,

    -- Waste / Inventory
    coalesce(mw.monthly_waste_cost, 0) as waste_cost,
    coalesce(mw.monthly_waste_events, 0) as waste_events,
    case
        when mr.monthly_revenue > 0
        then coalesce(mw.monthly_waste_cost, 0) * 100.0 / mr.monthly_revenue
        else 0
    end as waste_pct_revenue,

    -- Financial (from PnL)
    sp.monthly_labor_cost as pnl_labor_cost,
    sp.operating_expenses as pnl_operating_expenses,
    sp.marketing_spend as pnl_marketing_spend,
    sp.inventory_holding_cost as pnl_inventory_holding_cost,
    sp.total_costs as pnl_total_costs,
    sp.net_profit,
    sp.net_profit_margin_pct as net_margin,
    sp.labor_cost_ratio_pct,
    sp.opex_ratio_pct,
    sp.marketing_ratio_pct,
    case
        when mr.monthly_revenue > 0
        then (mr.monthly_revenue - coalesce(sp.total_costs, 0))
        else 0
    end as gross_profit,
    case
        when mr.monthly_revenue > 0
        then (mr.monthly_revenue - coalesce(sp.total_costs, 0)) * 100.0 / mr.monthly_revenue
        else 0
    end as gross_margin,

    -- Marketing
    coalesce(mm.total_marketing_spend, 0) as campaign_spend,
    coalesce(mm.total_campaign_days, 0) as active_campaigns,
    coalesce(mm.coupon_redemptions, 0) as coupon_redemptions,

    -- Store scoring
    sh.store_health_score,
    sh.health_tier,
    sh.revenue_growth_score,
    sh.profitability_score,
    sh.labor_efficiency_score,
    sh.inventory_health_score,

    -- Derived efficiency
    round(mr.monthly_revenue / nullif(mc.tracked_active_customers, 0), 2) as revenue_per_active_customer,
    round(mr.monthly_revenue / nullif(ml.monthly_labor_hours, 0), 2) as revenue_per_labor_hour

from monthly_revenue as mr
left join locations as l
    on mr.location_id = l.location_id
left join monthly_labor as ml
    on mr.location_id = ml.location_id and mr.month_start = ml.month_start
left join monthly_customers as mc
    on mr.month_start = mc.month_start
left join store_pnl as sp
    on mr.location_id = sp.location_id and mr.month_start = sp.report_month
left join store_health as sh
    on mr.location_id = sh.location_id
left join monthly_waste as mw
    on mr.location_id = mw.location_id and mr.month_start = mw.month_start
left join monthly_inventory as mi
    on mr.location_id = mi.location_id and mr.month_start = mi.month_start
left join monthly_marketing as mm
    on mr.month_start = mm.month_start
left join monthly_product_sales as mps
    on mr.month_start = mps.month_start
left join product_mix as pm
    on mr.location_id = pm.location_id and mr.month_start = pm.order_month
left join customer_segments as cs
    on mr.location_id = cs.location_id and mr.month_start = cs.order_month
