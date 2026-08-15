with

daily_deliveries as (
    select
        actual_arrival_at,
        count(*) as total_deliveries,
        count(case when is_on_time then 1 end) as on_time_deliveries,
        round(count(case when is_on_time then 1 end) * 100.0 / nullif(count(*), 0), 2) as on_time_pct
    from {{ ref('fct_deliveries') }}
    group by 1
),

trended as (
    select
        actual_arrival_at,
        total_deliveries,
        on_time_deliveries,
        on_time_pct,
        avg(on_time_pct) over (order by actual_arrival_at rows between 6 preceding and current row) as on_time_7d_ma,
        avg(on_time_pct) over (order by actual_arrival_at rows between 27 preceding and current row) as on_time_28d_ma,
        case
            when on_time_pct < 80 then 'poor'
            when on_time_pct < 95 then 'acceptable'
            else 'excellent'
        end as delivery_performance_band
    from daily_deliveries
)

select * from trended
