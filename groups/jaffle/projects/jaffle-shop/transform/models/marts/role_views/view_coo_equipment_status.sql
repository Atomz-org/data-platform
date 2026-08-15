with

equipment_reliability as (
    select * from {{ ref('rpt_equipment_reliability') }}
)

select
    equipment_id,
    location_id,
    equipment_name,
    equipment_type,
    total_downtime_hours,
    total_maintenance_events,
    avg_downtime_per_event,
    emergency_pct,
    case
        when emergency_pct <= 2 then 'excellent'
        when emergency_pct <= 5 then 'good'
        when emergency_pct <= 10 then 'fair'
        else 'needs_replacement'
    end as equipment_condition,
    case
        when emergency_pct > 10 then true
        else false
    end as requires_attention

from equipment_reliability
