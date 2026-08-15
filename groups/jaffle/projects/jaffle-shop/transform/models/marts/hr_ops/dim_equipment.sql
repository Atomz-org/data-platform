with

equipment as (

    select * from {{ ref('stg_equipment') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

final as (

    select
        equipment.equipment_id,
        equipment.location_id,
        locations.location_name,
        equipment.equipment_name,
        equipment.equipment_type,
        equipment.manufacturer,
        equipment.model_number,
        equipment.serial_number,
        equipment.equipment_status,
        equipment.purchase_cost,
        equipment.purchase_date,
        equipment.warranty_expiry_date,
        equipment.last_maintenance_date,
        case
            when equipment.warranty_expiry_date >= current_date then true
            else false
        end as is_under_warranty,
        {{ dbt.datediff('equipment.purchase_date', 'current_date', 'day') }} as equipment_age_days

    from equipment
    left join locations
        on equipment.location_id = locations.location_id

)

select * from final
