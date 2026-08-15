with

maintenance_logs as (

    select * from {{ ref('stg_maintenance_logs') }}

),

equipment as (

    select * from {{ ref('stg_equipment') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

final as (

    select
        maintenance_logs.maintenance_log_id,
        maintenance_logs.equipment_id,
        equipment.equipment_name,
        equipment.equipment_type,
        equipment.location_id,
        locations.location_name,
        maintenance_logs.technician_id,
        maintenance_logs.maintenance_type,
        maintenance_logs.maintenance_description,
        maintenance_logs.maintenance_status,
        maintenance_logs.maintenance_cost,
        maintenance_logs.downtime_hours,
        maintenance_logs.scheduled_date,
        maintenance_logs.completed_date,
        case
            when equipment.warranty_expiry_date >= maintenance_logs.scheduled_date
                then true
            else false
        end as is_under_warranty,
        case
            when maintenance_logs.maintenance_type = 'emergency' then true
            else false
        end as is_emergency

    from maintenance_logs
    inner join equipment
        on maintenance_logs.equipment_id = equipment.equipment_id
    left join locations
        on equipment.location_id = locations.location_id

)

select * from final
