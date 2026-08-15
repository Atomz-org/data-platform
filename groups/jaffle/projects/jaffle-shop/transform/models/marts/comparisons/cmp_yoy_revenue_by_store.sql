with

monthly_orders as (

    select * from {{ ref('int_monthly_orders_by_store') }}

),

yoy_comparison as (

    select
        curr.location_id,
        curr.location_name,
        curr.month_start as current_month,
        curr.total_revenue as current_revenue,
        curr.order_count as current_orders,
        prev.total_revenue as prior_year_revenue,
        prev.order_count as prior_year_orders,
        curr.total_revenue - coalesce(prev.total_revenue, 0) as revenue_change,
        case
            when prev.total_revenue > 0
            then round(
                (curr.total_revenue - prev.total_revenue) / prev.total_revenue * 100, 2
            )
            else null
        end as yoy_revenue_growth_pct,
        case
            when prev.order_count > 0
            then round(
                (curr.order_count - prev.order_count) * 100.0 / prev.order_count, 2
            )
            else null
        end as yoy_order_growth_pct,
        case
            when curr.order_count > 0
            then round(curr.total_revenue * 1.0 / curr.order_count, 2)
            else 0
        end as current_avg_order_value,
        case
            when prev.order_count > 0
            then round(prev.total_revenue * 1.0 / prev.order_count, 2)
            else 0
        end as prior_year_avg_order_value
    from monthly_orders as curr
    left join monthly_orders as prev
        on curr.location_id = prev.location_id
        and {{ dbt.dateadd('month', -12, 'curr.month_start') }} = prev.month_start

)

select * from yoy_comparison
