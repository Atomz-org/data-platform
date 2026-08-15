with

maintenance_logs as (

    select * from {{ ref('stg_maintenance_logs') }}

),

equipment as (

    select
        equipment_id,
        equipment_name,
        equipment_type,
        location_id
    from {{ ref('stg_equipment') }}

),

final as (

    select
        eq.equipment_type,
        eq.location_id,
        count(ml.maintenance_log_id) as total_maintenance_events,
        count(case when ml.maintenance_type = 'preventive' then 1 end) as preventive_count,
        count(case when ml.maintenance_type = 'corrective' then 1 end) as corrective_count,
        count(case when ml.maintenance_type = 'emergency' then 1 end) as emergency_count,
        sum(ml.maintenance_cost) as total_maintenance_cost,
        avg(ml.maintenance_cost) as avg_maintenance_cost,
        sum(ml.downtime_hours) as total_downtime_hours,
        avg(ml.downtime_hours) as avg_downtime_hours,
        count(distinct eq.equipment_id) as equipment_count,
        case
            when count(distinct eq.equipment_id) > 0
                then round(cast(count(ml.maintenance_log_id) * 1.0 / count(distinct eq.equipment_id) as {{ dbt.type_float() }}), 2)
            else 0
        end as avg_events_per_equipment
    from maintenance_logs as ml
    inner join equipment as eq
        on ml.equipment_id = eq.equipment_id
    group by 1, 2

)

select * from final
