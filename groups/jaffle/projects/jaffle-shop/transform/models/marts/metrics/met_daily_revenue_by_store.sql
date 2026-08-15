with

daily_revenue as (

    select * from {{ ref('int_daily_revenue') }}

),

locations as (

    select
        location_id,
        location_name
    from {{ ref('stg_locations') }}

),

enriched as (

    select
        dr.revenue_date,
        dr.location_id,
        coalesce(l.location_name, 'Unknown') as store_name,
        dr.invoice_count as order_count,
        dr.total_revenue,
        dr.avg_invoice_amount as avg_order_value,
        dr.gross_revenue,
        dr.tax_collected,

        -- 7-day rolling averages
        avg(dr.total_revenue) over (
            partition by dr.location_id
            order by dr.revenue_date
            rows between 6 preceding and current row
        ) as revenue_7d_avg,
        avg(dr.invoice_count) over (
            partition by dr.location_id
            order by dr.revenue_date
            rows between 6 preceding and current row
        ) as orders_7d_avg,

        -- 28-day rolling averages
        avg(dr.total_revenue) over (
            partition by dr.location_id
            order by dr.revenue_date
            rows between 27 preceding and current row
        ) as revenue_28d_avg,
        avg(dr.invoice_count) over (
            partition by dr.location_id
            order by dr.revenue_date
            rows between 27 preceding and current row
        ) as orders_28d_avg

    from daily_revenue as dr

    left join locations as l
        on dr.location_id = l.location_id

)

select * from enriched
