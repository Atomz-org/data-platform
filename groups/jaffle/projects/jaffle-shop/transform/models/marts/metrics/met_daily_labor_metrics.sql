with

labor as (

    select * from {{ ref('int_labor_cost_daily') }}

),

orders as (

    select * from {{ ref('int_daily_orders_by_store') }}

),

final as (

    select
        labor.work_date,
        labor.location_id,
        orders.location_name as store_name,
        labor.total_hours as total_labor_hours,
        labor.total_labor_cost,
        labor.employee_count,
        coalesce(orders.order_count, 0) as order_count,
        coalesce(orders.total_revenue, 0) as daily_revenue,
        case
            when labor.total_hours > 0
            then coalesce(orders.order_count, 0) * 1.0 / labor.total_hours
            else 0
        end as orders_per_labor_hour,
        case
            when coalesce(orders.total_revenue, 0) > 0
            then labor.total_labor_cost * 100.0 / orders.total_revenue
            else null
        end as labor_cost_pct_of_revenue,
        case
            when labor.total_hours > 0
            then coalesce(orders.total_revenue, 0) / labor.total_hours
            else 0
        end as revenue_per_labor_hour

    from labor

    left join orders
        on labor.location_id = orders.location_id
        and labor.work_date = orders.order_date

)

select * from final
