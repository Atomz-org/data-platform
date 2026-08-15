with

daily_waste as (
    select
        waste_date,
        location_id,
        total_waste_cost,
        avg(total_waste_cost) over (
            partition by location_id order by waste_date
            rows between 14 preceding and 1 preceding
        ) as waste_14d_avg
    from {{ ref('met_daily_waste_metrics') }}
),

alerts as (
    select
        waste_date,
        location_id,
        total_waste_cost,
        waste_14d_avg,
        round(total_waste_cost * 100.0 / nullif(waste_14d_avg, 0), 2) as pct_of_avg,
        'waste_spike' as alert_type,
        'warning' as severity
    from daily_waste
    where total_waste_cost > waste_14d_avg * 2.5
      and waste_14d_avg > 0
)

select * from alerts
