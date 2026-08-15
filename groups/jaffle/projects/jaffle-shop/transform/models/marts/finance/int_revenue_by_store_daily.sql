with

daily_revenue as (

    select * from {{ ref('int_daily_revenue') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

store_daily as (

    select
        dr.revenue_date,
        dr.location_id,
        l.location_name,
        l.opened_date as store_opened_date,
        dr.invoice_count,
        dr.gross_revenue,
        dr.tax_collected,
        dr.total_revenue,
        dr.avg_invoice_amount,
        sum(dr.total_revenue) over (
            partition by dr.location_id
            order by dr.revenue_date
            rows between 6 preceding and current row
        ) as rolling_7d_revenue,
        avg(dr.total_revenue) over (
            partition by dr.location_id
            order by dr.revenue_date
            rows between 6 preceding and current row
        ) as avg_7d_revenue,
        lag(dr.total_revenue, 1) over (
            partition by dr.location_id
            order by dr.revenue_date
        ) as prev_day_revenue,
        case
            when lag(dr.total_revenue, 1) over (
                partition by dr.location_id
                order by dr.revenue_date
            ) > 0
                then (dr.total_revenue - lag(dr.total_revenue, 1) over (
                    partition by dr.location_id
                    order by dr.revenue_date
                )) / lag(dr.total_revenue, 1) over (
                    partition by dr.location_id
                    order by dr.revenue_date
                )
            else null
        end as dod_growth_rate

    from daily_revenue as dr
    left join locations as l
        on dr.location_id = l.location_id

)

select * from store_daily
