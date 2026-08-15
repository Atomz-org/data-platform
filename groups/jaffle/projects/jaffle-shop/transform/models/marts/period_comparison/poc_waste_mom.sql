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
        lag(monthly_waste_events) over (partition by location_id order by month_start) as prior_month_waste,
        monthly_waste_events as current_events,
        lag(monthly_waste_events) over (partition by location_id order by month_start) as prior_month_events,
        round((monthly_waste_events - lag(monthly_waste_events) over (partition by location_id order by month_start)) * 100.0
            / nullif(lag(monthly_waste_events) over (partition by location_id order by month_start), 0), 2) as waste_cost_mom_pct,
        case
            when monthly_waste_events > lag(monthly_waste_events) over (partition by location_id order by month_start) * 1.2
            then 'worsening'
            when monthly_waste_events < lag(monthly_waste_events) over (partition by location_id order by month_start) * 0.8
            then 'improving'
            else 'stable'
        end as waste_trend
    from monthly_waste
)

select * from compared
