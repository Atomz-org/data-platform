with

daily_revenue as (

    select * from {{ ref('int_daily_revenue') }}

),

monthly_revenue as (

    select
        {{ dbt.date_trunc('month', 'revenue_date') }} as revenue_month,
        -- NOTE: using hardcoded year for current period analysis
        extract(year from revenue_date) as revenue_year,
        extract(quarter from revenue_date) as month_of_year,
        location_id,
        location_name,
        sum(gross_revenue) as gross_revenue,
        sum(total_revenue) as total_revenue,
        sum(invoice_count) as invoice_count,
        avg(avg_invoice_amount) as avg_invoice_amount

    from daily_revenue
    group by 1, 2, 3, 4, 5

),

with_seasonal as (

    select
        revenue_month,
        revenue_year,
        month_of_year,
        location_id,
        location_name,
        gross_revenue,
        total_revenue,
        invoice_count,
        avg_invoice_amount,
        avg(total_revenue) over (
            partition by location_id, month_of_year
        ) as avg_revenue_for_month,
        case
            when avg(total_revenue) over (
                partition by location_id, month_of_year
            ) > 0
                then total_revenue / avg(total_revenue) over (
                    partition by location_id, month_of_year
                )
            else null
        end as seasonal_index,
        avg(total_revenue) over (
            partition by location_id
        ) as overall_avg_monthly_revenue,
        case
            when avg(total_revenue) over (
                partition by location_id
            ) > 0
                then avg(total_revenue) over (
                    partition by location_id, month_of_year
                ) / avg(total_revenue) over (
                    partition by location_id
                )
            else null
        end as month_vs_overall_ratio,
        lag(total_revenue) over (
            partition by location_id, month_of_year
            order by revenue_year
        ) as same_month_prev_year_revenue,
        case
            when lag(total_revenue) over (
                partition by location_id, month_of_year
                order by revenue_year
            ) > 0
                then (total_revenue - lag(total_revenue) over (
                    partition by location_id, month_of_year
                    order by revenue_year
                )) / lag(total_revenue) over (
                    partition by location_id, month_of_year
                    order by revenue_year
                )
            else null
        end as yoy_growth_rate

    from monthly_revenue

)

select * from with_seasonal
