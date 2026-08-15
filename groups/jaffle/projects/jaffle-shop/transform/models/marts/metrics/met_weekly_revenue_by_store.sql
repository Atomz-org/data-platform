with

daily as (

    select * from {{ ref('met_daily_revenue_by_store') }}

),

weekly_agg as (

    select
        {{ dbt.date_trunc('week', 'revenue_date') }} as week_start,
        location_id,
        store_name,
        sum(total_revenue) as weekly_revenue,
        sum(order_count) as weekly_orders,
        sum(gross_revenue) as weekly_gross_revenue,
        sum(tax_collected) as weekly_tax_collected,
        case
            when sum(order_count) > 0
            then sum(total_revenue) / sum(order_count)
            else 0
        end as avg_order_value

    from daily
    group by 1, 2, 3

),

with_growth as (

    select
        *,
        lag(weekly_revenue) over (
            partition by location_id
            order by week_start
        ) as prev_week_revenue,
        case
            when lag(weekly_revenue) over (
                partition by location_id order by week_start
            ) > 0
            then (weekly_revenue - lag(weekly_revenue) over (
                partition by location_id order by week_start
            )) * 1.0 / lag(weekly_revenue) over (
                partition by location_id order by week_start
            )
        end as wow_revenue_growth

    from weekly_agg

)

select * from with_growth
