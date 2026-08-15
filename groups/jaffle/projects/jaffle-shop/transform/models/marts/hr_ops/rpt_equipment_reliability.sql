with

downtime as (

    select * from {{ ref('int_equipment_downtime') }}

),

equipment as (

    select * from {{ ref('dim_equipment') }}

),

reliability_by_equipment as (

    select
        downtime.equipment_id,
        equipment.equipment_name,
        equipment.equipment_type,
        equipment.location_id,
        equipment.location_name,
        equipment.equipment_age_days,
        equipment.is_under_warranty,
        sum(downtime.maintenance_event_count) as total_maintenance_events,
        sum(downtime.total_downtime_hours) as total_downtime_hours,
        sum(downtime.total_maintenance_cost) as total_maintenance_cost,
        sum(downtime.emergency_count) as total_emergency_events,
        sum(downtime.preventive_count) as total_preventive_events,
        avg(downtime.total_downtime_hours) as avg_monthly_downtime_hours,
        case
            when sum(downtime.maintenance_event_count) > 0
                then round(
                    (sum(downtime.total_downtime_hours)
                    / sum(downtime.maintenance_event_count)), 1
                )
            else 0
        end as avg_downtime_per_event,
        case
            when sum(downtime.maintenance_event_count) > 0
                then round(
                    (sum(downtime.emergency_count) * 100.0
                    / sum(downtime.maintenance_event_count)), 1
                )
            else 0
        end as emergency_pct

    from downtime
    inner join equipment
        on downtime.equipment_id = equipment.equipment_id
    group by
        downtime.equipment_id,
        equipment.equipment_name,
        equipment.equipment_type,
        equipment.location_id,
        equipment.location_name,
        equipment.equipment_age_days,
        equipment.is_under_warranty

)

select * from reliability_by_equipment
