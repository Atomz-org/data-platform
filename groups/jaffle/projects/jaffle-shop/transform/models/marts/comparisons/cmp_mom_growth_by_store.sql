with

monthly_orders as (

    select * from {{ ref('int_monthly_orders_by_store') }}

),

mom_comparison as (

    select
        curr.location_id,
        curr.location_name,
        curr.month_start as current_month,
        curr.total_revenue as current_revenue,
        curr.order_count as current_orders,
        curr.unique_customer_visits as current_customers,
        prev.total_revenue as prior_month_revenue,
        prev.order_count as prior_month_orders,
        prev.unique_customer_visits as prior_month_customers,

        -- Revenue growth
        case
            when prev.total_revenue > 0
            then round(
                (curr.total_revenue - prev.total_revenue) / prev.total_revenue * 100, 2
            )
            else null
        end as mom_revenue_growth_pct,

        -- Order growth
        case
            when prev.order_count > 0
            then round(
                (curr.order_count - prev.order_count) * 100.0 / prev.order_count, 2
            )
            else null
        end as mom_order_growth_pct,

        -- Customer growth
        case
            when prev.unique_customer_visits > 0
            then round(
                (curr.unique_customer_visits - prev.unique_customer_visits) * 100.0
                / prev.unique_customer_visits, 2
            )
            else null
        end as mom_customer_growth_pct,

        -- 3-month trailing average revenue
        avg(curr.total_revenue) over (
            partition by curr.location_id
            order by curr.month_start
            rows between 2 preceding and current row
        ) as trailing_3m_avg_revenue

    from monthly_orders as curr
    left join monthly_orders as prev
        on curr.location_id = prev.location_id
        and {{ dbt.dateadd('month', -1, 'curr.month_start') }} = prev.month_start

)

select * from mom_comparison
