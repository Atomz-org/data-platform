with

equipment as (
    select * from {{ ref('stg_equipment') }}
),

locations as (
    select location_id, location_name from {{ ref('stg_locations') }}
),

final as (
    select
        eq.equipment_id,
        eq.equipment_name,
        eq.equipment_type,
        eq.location_id,
        l.location_name,
        eq.purchase_date,
        eq.equipment_status
    from equipment as eq
    left join locations as l on eq.location_id = l.location_id
)

select * from final
