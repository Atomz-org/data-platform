with

labor_metrics as (

    select
        month_start,
        sum(monthly_labor_cost) as total_labor_cost,
        sum(monthly_revenue) as total_revenue,
        avg(orders_per_labor_hour) as avg_orders_per_labor_hour,
        avg(labor_cost_pct_of_revenue) as avg_labor_cost_pct
    from {{ ref('met_monthly_labor_metrics') }}
    where month_start = (
        select max(month_start) from {{ ref('met_monthly_labor_metrics') }}
    )
    group by month_start

),

inventory_metrics as (

    select
        month_start,
        sum(monthly_movements) as total_inventory_movements,
        sum(monthly_inbound) as total_inbound,
        sum(monthly_outbound) as total_outbound,
        avg(products_in_stock) as avg_products_in_stock
    from {{ ref('met_monthly_inventory_metrics') }}
    where month_start = (
        select max(month_start) from {{ ref('met_monthly_inventory_metrics') }}
    )
    group by month_start

),

waste_metrics as (

    select
        month_start,
        sum(monthly_waste_cost) as total_waste_cost,
        sum(monthly_waste_events) as total_waste_events,
        avg(waste_to_revenue_pct) as avg_waste_to_revenue_pct
    from {{ ref('met_monthly_waste_metrics') }}
    where month_start = (
        select max(month_start) from {{ ref('met_monthly_waste_metrics') }}
    )
    group by month_start

),

employee_performance as (

    select
        avg(performance_score) as avg_employee_score,
        count(case when performance_tier = 'top_performer' then 1 end) as top_performers,
        count(case when performance_tier = 'needs_support' then 1 end) as needs_support_count,
        count(*) as total_scored_employees
    from {{ ref('scr_employee_performance') }}

),

final as (

    select
        coalesce(lm.month_start, im.month_start, wm.month_start) as reporting_month,

        -- Labor efficiency
        coalesce(lm.avg_orders_per_labor_hour, 0) as avg_orders_per_labor_hour,
        coalesce(lm.avg_labor_cost_pct, 0) as labor_cost_pct,
        coalesce(lm.total_labor_cost, 0) as total_labor_cost,

        -- Inventory health
        coalesce(im.total_inventory_movements, 0) as inventory_movements,
        coalesce(im.avg_products_in_stock, 0) as avg_products_in_stock,
        coalesce(im.total_inbound, 0) as total_inbound,
        coalesce(im.total_outbound, 0) as total_outbound,

        -- Waste control
        coalesce(wm.total_waste_cost, 0) as waste_cost,
        coalesce(wm.total_waste_events, 0) as waste_events,
        coalesce(wm.avg_waste_to_revenue_pct, 0) as waste_to_revenue_pct,

        -- Employee performance
        coalesce(ep.avg_employee_score, 0) as avg_employee_performance_score,
        coalesce(ep.top_performers, 0) as top_performers,
        coalesce(ep.needs_support_count, 0) as needs_support_count,
        coalesce(ep.total_scored_employees, 0) as total_scored_employees,

        -- Operations health score (composite)
        round(-- Labor efficiency (25 pts): lower labor % = better
            (case
                when coalesce(lm.avg_labor_cost_pct, 100) <= 25 then 25
                when coalesce(lm.avg_labor_cost_pct, 100) <= 35 then 18
                when coalesce(lm.avg_labor_cost_pct, 100) <= 45 then 10
                else 5
            end)
            -- Waste control (25 pts): lower waste % = better
            + (case
                when coalesce(wm.avg_waste_to_revenue_pct, 100) <= 1 then 25
                when coalesce(wm.avg_waste_to_revenue_pct, 100) <= 3 then 18
                when coalesce(wm.avg_waste_to_revenue_pct, 100) <= 5 then 10
                else 5
            end)
            -- Inventory activity (25 pts)
            + (case
                when coalesce(im.total_inventory_movements, 0) >= 500 then 25
                when coalesce(im.total_inventory_movements, 0) >= 200 then 18
                when coalesce(im.total_inventory_movements, 0) >= 50 then 10
                else 5
            end)
            -- Employee performance (25 pts)
            + (case
                when coalesce(ep.avg_employee_score, 0) >= 75 then 25
                when coalesce(ep.avg_employee_score, 0) >= 55 then 18
                when coalesce(ep.avg_employee_score, 0) >= 35 then 10
                else 5
            end), 0) as ops_health_score

    from labor_metrics as lm

    full outer join inventory_metrics as im
        on lm.month_start = im.month_start

    full outer join waste_metrics as wm
        on coalesce(lm.month_start, im.month_start) = wm.month_start

    cross join employee_performance as ep

)

select * from final
