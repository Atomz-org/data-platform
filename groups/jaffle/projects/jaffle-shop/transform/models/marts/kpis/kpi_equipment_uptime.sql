with final as (
    select
        equipment_id,
        location_id,
        age_days,
        total_downtime_hours,
        age_days - coalesce(total_downtime_hours, 0) as uptime_days,
        round((age_days - coalesce(total_downtime_hours, 0)) * 100.0
            / nullif(age_days, 0), 2) as uptime_pct
    from {{ ref('int_equipment_lifecycle') }}
)
select * from final
