with

daily_kpis as (

    select * from {{ ref('exec_company_kpis_daily') }}

),

monthly_agg as (

    select
        {{ dbt.date_trunc('month', 'kpi_date') }} as month_start,
        sum(total_revenue) as monthly_revenue,
        sum(total_orders) as monthly_orders,
        sum(total_gross_revenue) as monthly_gross_revenue,
        sum(total_tax_collected) as monthly_tax,
        case
            when sum(total_orders) > 0
            then sum(total_revenue) / sum(total_orders)
            else 0
        end as avg_ticket_size,
        sum(new_customers) as monthly_new_customers,
        avg(active_customers) as avg_daily_active_customers,
        sum(total_waste_cost) as monthly_waste_cost,
        count(kpi_date) as active_days

    from daily_kpis
    group by 1

),

with_growth as (

    select
        *,
        -- MoM growth
        lag(monthly_revenue) over (order by month_start) as prev_month_revenue,
        case
            when lag(monthly_revenue) over (order by month_start) > 0
            then (monthly_revenue - lag(monthly_revenue) over (order by month_start))
                * 1.0 / lag(monthly_revenue) over (order by month_start)
        end as mom_revenue_growth,
        case
            when lag(monthly_orders) over (order by month_start) > 0
            then (monthly_orders - lag(monthly_orders) over (order by month_start))
                * 1.0 / lag(monthly_orders) over (order by month_start)
        end as mom_orders_growth,

        -- YoY growth
        lag(monthly_revenue, 12) over (order by month_start) as same_month_last_year_revenue,
        case
            when lag(monthly_revenue, 12) over (order by month_start) > 0
            then (monthly_revenue - lag(monthly_revenue, 12) over (order by month_start))
                * 1.0 / lag(monthly_revenue, 12) over (order by month_start)
        end as yoy_revenue_growth

    from monthly_agg

)

select * from with_growth
