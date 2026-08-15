with

equipment as (

    select * from {{ ref('stg_equipment') }}

),

maintenance as (

    select
        equipment_id,
        sum(maintenance_cost) as total_maintenance_cost,
        count(maintenance_log_id) as maintenance_event_count,
        sum(downtime_hours) as total_downtime_hours
    from {{ ref('stg_maintenance_logs') }}
    group by 1

),

final as (

    select
        eq.location_id,
        count(distinct eq.equipment_id) as equipment_count,
        sum(eq.purchase_cost) as total_purchase_cost,
        sum(coalesce(m.total_maintenance_cost, 0)) as total_maintenance_cost,
        sum(eq.purchase_cost) + sum(coalesce(m.total_maintenance_cost, 0)) as total_equipment_cost,
        avg(eq.purchase_cost) as avg_purchase_cost,
        sum(coalesce(m.maintenance_event_count, 0)) as total_maintenance_events,
        sum(coalesce(m.total_downtime_hours, 0)) as total_downtime_hours,
        case
            when count(distinct eq.equipment_id) > 0
                then round(cast(
                    (sum(eq.purchase_cost) + sum(coalesce(m.total_maintenance_cost, 0)))
                    / count(distinct eq.equipment_id)
                as {{ dbt.type_float() }}), 2)
            else 0
        end as avg_total_cost_per_equipment
    from equipment as eq
    left join maintenance as m
        on eq.equipment_id = m.equipment_id
    group by 1

)

select * from final
