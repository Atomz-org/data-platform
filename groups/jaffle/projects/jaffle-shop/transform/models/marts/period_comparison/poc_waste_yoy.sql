with

monthly_waste as (
    select
        month_start,
        location_id,
        monthly_waste_events
    from {{ ref('met_monthly_waste_metrics') }}
),

compared as (
    select
        month_start,
        location_id,
        monthly_waste_events as current_waste,
        lag(monthly_waste_events, 12) over (partition by location_id order by month_start) as prior_year_waste,
        round((monthly_waste_events - lag(monthly_waste_events, 12) over (partition by location_id order by month_start)) * 100.0
            / nullif(lag(monthly_waste_events, 12) over (partition by location_id order by month_start), 0), 2) as waste_yoy_pct
    from monthly_waste
)

select * from compared
