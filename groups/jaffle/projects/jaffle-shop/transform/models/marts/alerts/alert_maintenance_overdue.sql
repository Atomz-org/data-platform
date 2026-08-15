with

equipment_health as (
    select
        equipment_id,
        location_id,
        equipment_name,
        equipment_status,
        age_days,
        total_maintenance_events,
        preventive_events,
        total_downtime_hours
    from {{ ref('int_equipment_lifecycle') }}
),

alerts as (
    select
        equipment_id,
        location_id,
        equipment_name,
        age_days,
        total_maintenance_events,
        preventive_events,
        'maintenance_overdue' as alert_type,
        case
            when preventive_events = 0 and age_days > 180 then 'critical'
            when preventive_events = 0 and age_days > 90 then 'warning'
            else 'info'
        end as severity
    from equipment_health
    where equipment_status = 'active'
      and (preventive_events = 0 and age_days > 90)
)

select * from alerts
