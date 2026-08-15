with

equipment_health as (
    select
        equipment_id,
        location_id,
        equipment_name,
        equipment_type,
        equipment_status,
        age_days,
        total_maintenance_events,
        total_downtime_hours,
        emergency_events
    from {{ ref('int_equipment_lifecycle') }}
),

alerts as (
    select
        equipment_id,
        location_id,
        equipment_name,
        equipment_type,
        age_days,
        total_maintenance_events,
        emergency_events,
        total_downtime_hours,
        'equipment_breakdown_risk' as alert_type,
        case
            when emergency_events > 3 then 'critical'
            when emergency_events > 1 then 'warning'
            else 'info'
        end as severity
    from equipment_health
    where emergency_events > 1
       or total_downtime_hours > 100
)

select * from alerts
