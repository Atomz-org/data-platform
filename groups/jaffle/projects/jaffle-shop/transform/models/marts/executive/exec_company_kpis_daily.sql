with

revenue as (

    select
        revenue_date,
        sum(total_revenue) as total_revenue,
        sum(order_count) as total_orders,
        sum(gross_revenue) as total_gross_revenue,
        sum(tax_collected) as total_tax_collected,
        case
            when sum(order_count) > 0
            then sum(total_revenue) / sum(order_count)
            else 0
        end as avg_ticket_size
    from {{ ref('met_daily_revenue_by_store') }}
    group by revenue_date

),

customers as (

    select
        activity_date,
        active_customers,
        new_customers,
        returning_customers
    from {{ ref('met_daily_customer_metrics') }}

),

waste as (

    select
        waste_date,
        sum(total_waste_cost) as total_waste_cost,
        sum(waste_events) as total_waste_events
    from {{ ref('met_daily_waste_metrics') }}
    group by waste_date

),

final as (

    select
        r.revenue_date as kpi_date,
        r.total_revenue,
        r.total_orders,
        r.total_gross_revenue,
        r.total_tax_collected,
        r.avg_ticket_size,
        coalesce(c.active_customers, 0) as active_customers,
        coalesce(c.new_customers, 0) as new_customers,
        coalesce(c.returning_customers, 0) as returning_customers,
        coalesce(w.total_waste_cost, 0) as total_waste_cost,
        coalesce(w.total_waste_events, 0) as total_waste_events,

        -- Gross margin proxy: revenue - waste cost
        r.total_revenue - coalesce(w.total_waste_cost, 0) as net_revenue_after_waste,

        -- Rolling metrics
        avg(r.total_revenue) over (
            order by r.revenue_date
            rows between 6 preceding and current row
        ) as revenue_7d_avg,
        avg(r.total_orders) over (
            order by r.revenue_date
            rows between 6 preceding and current row
        ) as orders_7d_avg

    from revenue as r

    left join customers as c
        on r.revenue_date = c.activity_date

    left join waste as w
        on r.revenue_date = w.waste_date

)

select * from final
