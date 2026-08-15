with final as (
    select
        month_start,
        location_id,
        monthly_waste_events,
        round(monthly_waste_events * 1.0 / nullif(monthly_waste_events, 0), 2) as avg_waste_per_event,
        lag(monthly_waste_events) over (partition by location_id order by month_start) as prior_month_waste
    from {{ ref('met_monthly_waste_metrics') }}
)
select * from final
