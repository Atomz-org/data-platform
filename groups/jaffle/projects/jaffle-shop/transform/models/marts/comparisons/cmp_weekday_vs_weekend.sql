with

orders as (

    select * from {{ ref('stg_orders') }}

),

date_spine as (

    select * from {{ ref('util_date_spine') }}

),

order_with_daytype as (

    select
        o.order_id,
        o.customer_id,
        o.location_id,
        o.ordered_at,
        o.order_total,
        o.subtotal,
        ds.is_weekend,
        case when ds.is_weekend then 'weekend' else 'weekday' end as day_type
    from orders as o
    inner join date_spine as ds
        on o.ordered_at = ds.date_day

),

store_daytype_metrics as (

    select
        location_id,
        day_type,
        count(distinct order_id) as total_orders,
        count(distinct ordered_at) as active_days,
        sum(order_total) as total_revenue,
        avg(order_total) as avg_order_value,
        count(distinct customer_id) as unique_customers,
        round(count(distinct order_id) * 1.0 / nullif(count(distinct ordered_at), 0), 2) as avg_orders_per_day,
        round(sum(order_total) * 1.0 / nullif(count(distinct ordered_at), 0), 2) as avg_revenue_per_day
    from order_with_daytype
    group by 1, 2

),

pivoted as (

    select
        wd.location_id,
        wd.total_orders as weekday_orders,
        wd.avg_orders_per_day as weekday_avg_orders_per_day,
        wd.avg_revenue_per_day as weekday_avg_revenue_per_day,
        wd.avg_order_value as weekday_avg_ticket,
        wd.unique_customers as weekday_unique_customers,
        we.total_orders as weekend_orders,
        we.avg_orders_per_day as weekend_avg_orders_per_day,
        we.avg_revenue_per_day as weekend_avg_revenue_per_day,
        we.avg_order_value as weekend_avg_ticket,
        we.unique_customers as weekend_unique_customers,
        case
            when wd.avg_revenue_per_day > 0
            then round(
                (we.avg_revenue_per_day - wd.avg_revenue_per_day)
                / wd.avg_revenue_per_day * 100, 2
            )
            else null
        end as weekend_revenue_lift_pct,
        case
            when wd.avg_order_value > 0
            then round(
                (we.avg_order_value - wd.avg_order_value)
                / wd.avg_order_value * 100, 2
            )
            else null
        end as weekend_ticket_lift_pct
    from store_daytype_metrics as wd
    inner join store_daytype_metrics as we
        on wd.location_id = we.location_id
    where wd.day_type = 'weekday'
        and we.day_type = 'weekend'

)

select * from pivoted
