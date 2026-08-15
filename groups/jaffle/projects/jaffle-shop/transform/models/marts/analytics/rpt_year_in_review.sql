with

monthly_revenue as (

    select
        month_start,
        sum(monthly_revenue) as total_revenue,
        sum(monthly_orders) as total_orders
    from {{ ref('met_monthly_revenue_by_store') }}
    group by 1

),

annual_metrics as (

    select
        extract(year from month_start) as fiscal_year,
        sum(total_revenue) as annual_revenue,
        sum(total_orders) as annual_orders,
        avg(total_revenue) as avg_monthly_revenue,
        min(total_revenue) as min_monthly_revenue,
        max(total_revenue) as max_monthly_revenue,
        count(distinct month_start) as months_of_data
    from monthly_revenue
    group by 1

),

yoy as (

    select
        fiscal_year,
        annual_revenue,
        annual_orders,
        avg_monthly_revenue,
        min_monthly_revenue,
        max_monthly_revenue,
        months_of_data,
        lag(annual_revenue) over (order by fiscal_year) as prev_year_revenue,
        lag(annual_orders) over (order by fiscal_year) as prev_year_orders,
        case
            when lag(annual_revenue) over (order by fiscal_year) > 0
                then round(cast(
                    (annual_revenue - lag(annual_revenue) over (order by fiscal_year)) * 100.0
                    / lag(annual_revenue) over (order by fiscal_year)
                as {{ dbt.type_float() }}), 2)
            else null
        end as revenue_yoy_growth_pct,
        case
            when annual_orders > 0
                then round(cast(annual_revenue / annual_orders as {{ dbt.type_float() }}), 2)
            else 0
        end as avg_order_value
    from annual_metrics

)

select * from yoy
