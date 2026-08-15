with

daily_revenue as (

    select * from {{ ref('int_daily_revenue') }}

),

weekly_agg as (

    select
        {{ dbt.date_trunc('week', 'revenue_date') }} as revenue_week,
        location_id,
        location_name,
        sum(invoice_count) as invoice_count,
        sum(gross_revenue) as gross_revenue,
        sum(tax_collected) as tax_collected,
        sum(total_revenue) as total_revenue,
        avg(avg_invoice_amount) as avg_invoice_amount,
        count(distinct revenue_date) as active_days

    from daily_revenue
    group by 1, 2, 3

),

with_growth as (

    select
        revenue_week,
        location_id,
        location_name,
        invoice_count,
        gross_revenue,
        tax_collected,
        total_revenue,
        avg_invoice_amount,
        active_days,
        lag(total_revenue) over (
            partition by location_id
            order by revenue_week
        ) as prev_week_revenue,
        case
            when lag(total_revenue) over (
                partition by location_id
                order by revenue_week
            ) > 0
                then (total_revenue - lag(total_revenue) over (
                    partition by location_id
                    order by revenue_week
                )) / lag(total_revenue) over (
                    partition by location_id
                    order by revenue_week
                )
            else null
        end as wow_growth_rate,
        avg(total_revenue) over (
            partition by location_id
            order by revenue_week
            rows between 3 preceding and current row
        ) as rolling_4w_avg_revenue

    from weekly_agg

)

select * from with_growth
