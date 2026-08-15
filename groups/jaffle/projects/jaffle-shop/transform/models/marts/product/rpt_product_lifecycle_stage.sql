with

product_sales_daily as (

    select * from {{ ref('int_product_sales_daily') }}

),

-- Calculate monthly sales to smooth daily variance
monthly_sales as (

    select
        product_id,
        product_name,
        product_type,
        {{ dbt.date_trunc('month', 'sale_date') }} as sale_month,
        sum(units_sold) as monthly_units_sold,
        sum(daily_revenue) as monthly_revenue,
        count(distinct sale_date) as active_days

    from product_sales_daily
    group by
        product_id,
        product_name,
        product_type,
        {{ dbt.date_trunc('month', 'sale_date') }}

),

with_trend as (

    select
        product_id,
        product_name,
        product_type,
        sale_month,
        monthly_units_sold,
        monthly_revenue,
        active_days,
        lag(monthly_units_sold) over (
            partition by product_id order by sale_month
        ) as prev_month_units,
        lag(monthly_units_sold, 2) over (
            partition by product_id order by sale_month
        ) as prev_2_month_units,
        lag(monthly_units_sold, 3) over (
            partition by product_id order by sale_month
        ) as prev_3_month_units,
        row_number() over (
            partition by product_id order by sale_month
        ) as month_number,
        count(*) over (partition by product_id) as total_months,
        avg(monthly_units_sold) over (
            partition by product_id
            order by sale_month
            rows between 2 preceding and current row
        ) as rolling_3m_avg_units,
        max(monthly_units_sold) over (partition by product_id) as peak_monthly_units

    from monthly_sales

),

-- Get the latest month per product for classification
latest_month as (

    select
        product_id,
        product_name,
        product_type,
        sale_month,
        monthly_units_sold,
        monthly_revenue,
        month_number,
        total_months,
        rolling_3m_avg_units,
        peak_monthly_units,
        prev_month_units,
        prev_2_month_units,
        -- Calculate recent trend (average of last 3 month-over-month changes)
        case
            when prev_month_units > 0
            then (monthly_units_sold - prev_month_units) * 1.0 / prev_month_units * 100
            else null
        end as latest_mom_change_pct,
        case
            when peak_monthly_units > 0
            then monthly_units_sold * 1.0 / peak_monthly_units * 100
            else null
        end as pct_of_peak,
        -- Lifecycle stage classification
        case
            when month_number <= 3 then 'introduction'
            when monthly_units_sold > coalesce(prev_month_units, 0)
                and monthly_units_sold > coalesce(prev_2_month_units, 0)
                and month_number <= total_months * 0.5
            then 'growth'
            when peak_monthly_units > 0
                and monthly_units_sold >= peak_monthly_units * 0.8
            then 'maturity'
            when peak_monthly_units > 0
                and monthly_units_sold < peak_monthly_units * 0.8
                and coalesce(prev_month_units, 0) >= monthly_units_sold
            then 'decline'
            else 'maturity'
        end as lifecycle_stage

    from with_trend
    where month_number = total_months

)

select * from latest_month
