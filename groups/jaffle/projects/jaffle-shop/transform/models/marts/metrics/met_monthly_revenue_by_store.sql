with

daily as (

    select * from {{ ref('met_daily_revenue_by_store') }}

),

fiscal as (

    select
        date_day,
        fiscal_year,
        fiscal_month,
        fiscal_quarter
    from {{ ref('util_fiscal_periods') }}

),

monthly_agg as (

    select
        {{ dbt.date_trunc('month', 'd.revenue_date') }} as month_start,
        d.location_id,
        d.store_name,
        max(f.fiscal_year) as fiscal_year,
        max(f.fiscal_month) as fiscal_month,
        max(f.fiscal_quarter) as fiscal_quarter,
        sum(d.total_revenue) as monthly_revenue,
        sum(d.order_count) as monthly_orders,
        sum(d.gross_revenue) as monthly_gross_revenue,
        sum(d.tax_collected) as monthly_tax_collected,
        case
            when sum(d.order_count) > 0
            then sum(d.total_revenue) / sum(d.order_count)
            else 0
        end as avg_order_value,
        count(d.revenue_date) as active_days

    from daily as d

    left join fiscal as f
        on d.revenue_date = f.date_day

    group by 1, 2, 3

),

with_growth as (

    select
        *,
        lag(monthly_revenue) over (
            partition by location_id order by month_start
        ) as prev_month_revenue,
        case
            when lag(monthly_revenue) over (
                partition by location_id order by month_start
            ) > 0
            then (monthly_revenue - lag(monthly_revenue) over (
                partition by location_id order by month_start
            )) * 1.0 / lag(monthly_revenue) over (
                partition by location_id order by month_start
            )
        end as mom_revenue_growth,
        lag(monthly_revenue, 12) over (
            partition by location_id order by month_start
        ) as same_month_last_year_revenue,
        case
            when lag(monthly_revenue, 12) over (
                partition by location_id order by month_start
            ) > 0
            then (monthly_revenue - lag(monthly_revenue, 12) over (
                partition by location_id order by month_start
            )) * 1.0 / lag(monthly_revenue, 12) over (
                partition by location_id order by month_start
            )
        end as yoy_revenue_growth

    from monthly_agg

)

select * from with_growth
