with

logs as (
    select * from {{ ref('stg_maintenance_logs') }}
),

equipment as (
    select equipment_id, equipment_name, equipment_type, location_id from {{ ref('stg_equipment') }}
),

final as (
    select
        ml.maintenance_log_id,
        ml.equipment_id,
        eq.equipment_name,
        eq.equipment_type,
        eq.location_id,
        ml.scheduled_date,
        ml.maintenance_type,
        ml.maintenance_cost,
        ml.maintenance_description
    from logs as ml
    left join equipment as eq on ml.equipment_id = eq.equipment_id
)

select * from final
