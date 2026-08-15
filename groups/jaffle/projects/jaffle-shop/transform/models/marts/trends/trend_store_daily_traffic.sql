with

daily_traffic as (
    select
        revenue_date as visit_date,
        location_id,
        order_count as transaction_count
    from {{ ref('met_daily_revenue_by_store') }}
),

trended as (
    select
        visit_date,
        location_id,
        transaction_count,
        avg(transaction_count) over (
            partition by location_id order by visit_date
            rows between 6 preceding and current row
        ) as traffic_7d_ma,
        avg(transaction_count) over (
            partition by location_id order by visit_date
            rows between 27 preceding and current row
        ) as traffic_28d_ma,
        transaction_count - lag(transaction_count, 7) over (
            partition by location_id order by visit_date
        ) as wow_change,
        case
            when transaction_count > avg(transaction_count) over (
                partition by location_id order by visit_date
                rows between 27 preceding and current row
            ) * 1.3 then 'high_traffic'
            when transaction_count < avg(transaction_count) over (
                partition by location_id order by visit_date
                rows between 27 preceding and current row
            ) * 0.7 then 'low_traffic'
            else 'normal'
        end as traffic_band
    from daily_traffic
)

select * from trended
