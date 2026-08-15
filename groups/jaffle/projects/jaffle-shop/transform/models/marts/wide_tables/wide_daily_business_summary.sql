with

daily_revenue as (

    select
        revenue_date as summary_date,
        sum(total_revenue) as total_revenue,
        sum(order_count) as total_orders

    from {{ ref('met_daily_revenue_by_store') }}
    group by revenue_date

),

daily_customers as (

    select
        activity_date as summary_date,
        sum(active_customers) as total_active_customers,
        sum(new_customers) as total_new_customers

    from {{ ref('met_daily_customer_metrics') }}
    group by activity_date

),

daily_labor as (

    select
        work_date as summary_date,
        sum(total_labor_cost) as total_labor_cost,
        sum(total_labor_hours) as total_labor_hours

    from {{ ref('met_daily_labor_metrics') }}
    group by work_date

),

daily_waste as (

    select
        waste_date as summary_date,
        sum(total_waste_cost) as total_waste_cost,
        sum(waste_events) as total_waste_events

    from {{ ref('met_daily_waste_metrics') }}
    group by waste_date

)

select
    dr.summary_date,
    dr.total_revenue,
    dr.total_orders,
    round(dr.total_revenue / nullif(dr.total_orders, 0), 2) as avg_order_value,
    dc.total_active_customers,
    dc.total_new_customers,
    dl.total_labor_cost,
    dl.total_labor_hours,
    dw.total_waste_cost,
    dw.total_waste_events,
    round(dl.total_labor_cost * 100.0 / nullif(dr.total_revenue, 0), 2) as labor_cost_pct,
    round(dw.total_waste_cost * 100.0 / nullif(dr.total_revenue, 0), 2) as waste_cost_pct

from daily_revenue dr
left join daily_customers dc on dr.summary_date = dc.summary_date
left join daily_labor dl on dr.summary_date = dl.summary_date
left join daily_waste dw on dr.summary_date = dw.summary_date
