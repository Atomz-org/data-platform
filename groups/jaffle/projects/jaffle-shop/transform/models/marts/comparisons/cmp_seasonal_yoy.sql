with

monthly_orders as (

    select * from {{ ref('int_monthly_orders_by_store') }}

),

fiscal as (

    select distinct
        month_start,
        fiscal_year,
        fiscal_quarter
    from {{ ref('util_fiscal_periods') }}

),

store_fiscal as (

    select
        mo.location_id,
        mo.location_name,
        f.fiscal_year,
        f.fiscal_quarter,
        sum(mo.total_revenue) as quarterly_revenue,
        sum(mo.order_count) as quarterly_orders,
        sum(mo.unique_customer_visits) as quarterly_customers
    from monthly_orders as mo
    inner join fiscal as f
        on mo.month_start = f.month_start
    group by 1, 2, 3, 4

),

yoy_seasonal as (

    select
        curr.location_id,
        curr.location_name,
        curr.fiscal_year as current_fiscal_year,
        curr.fiscal_quarter,
        curr.quarterly_revenue as current_revenue,
        curr.quarterly_orders as current_orders,
        prev.quarterly_revenue as prior_year_revenue,
        prev.quarterly_orders as prior_year_orders,
        curr.quarterly_revenue - coalesce(prev.quarterly_revenue, 0) as revenue_change,
        case
            when prev.quarterly_revenue > 0
            then round(
                (curr.quarterly_revenue - prev.quarterly_revenue)
                / prev.quarterly_revenue * 100, 2
            )
            else null
        end as yoy_revenue_growth_pct,
        case
            when prev.quarterly_orders > 0
            then round(
                (curr.quarterly_orders - prev.quarterly_orders) * 100.0
                / prev.quarterly_orders, 2
            )
            else null
        end as yoy_order_growth_pct
    from store_fiscal as curr
    left join store_fiscal as prev
        on curr.location_id = prev.location_id
        and curr.fiscal_quarter = prev.fiscal_quarter
        and curr.fiscal_year = prev.fiscal_year + 1

)

select * from yoy_seasonal
