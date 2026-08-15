with

orders as (

    select
        location_id,
        ordered_at as order_date,
        count(distinct order_id) as order_count,
        count(distinct customer_id) as unique_customers,
        sum(order_total) as daily_revenue,
        avg(order_total) as avg_order_value
    from {{ ref('stg_orders') }}
    group by 1, 2

),

labor as (

    select
        location_id,
        work_date,
        total_hours as labor_hours,
        total_labor_cost,
        employee_count
    from {{ ref('int_labor_cost_daily') }}

),

waste as (

    select
        location_id,
        cast(wasted_at as date) as waste_date,
        count(distinct waste_log_id) as waste_event_count,
        sum(quantity_wasted) as total_quantity_wasted,
        sum(cost_of_waste) as total_waste_cost
    from {{ ref('fct_waste_events') }}
    group by 1, 2

),

daily_summary as (

    select
        o.location_id,
        o.order_date,
        o.order_count,
        o.unique_customers,
        o.daily_revenue,
        o.avg_order_value,

        -- Labor metrics
        coalesce(l.labor_hours, 0) as labor_hours,
        coalesce(l.total_labor_cost, 0) as labor_cost,
        coalesce(l.employee_count, 0) as employees_on_duty,
        case
            when l.labor_hours > 0
            then round(o.daily_revenue / l.labor_hours, 2)
            else null
        end as revenue_per_labor_hour,
        case
            when l.labor_hours > 0
            then round(o.order_count * 1.0 / l.labor_hours, 2)
            else null
        end as orders_per_labor_hour,

        -- Waste metrics
        coalesce(w.waste_event_count, 0) as waste_events,
        coalesce(w.total_quantity_wasted, 0) as units_wasted,
        coalesce(w.total_waste_cost, 0) as waste_cost,
        case
            when o.daily_revenue > 0
            then round(coalesce(w.total_waste_cost, 0) / o.daily_revenue * 100, 2)
            else 0
        end as waste_as_pct_of_revenue

    from orders as o
    left join labor as l
        on o.location_id = l.location_id
        and o.order_date = l.work_date
    left join waste as w
        on o.location_id = w.location_id
        and o.order_date = w.waste_date

)

select * from daily_summary
