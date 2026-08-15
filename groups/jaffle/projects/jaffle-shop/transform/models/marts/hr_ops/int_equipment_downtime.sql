with

maintenance_logs as (

    select * from {{ ref('stg_maintenance_logs') }}

),

equipment as (

    select * from {{ ref('stg_equipment') }}

),

monthly_downtime as (

    select
        maintenance_logs.equipment_id,
        equipment.equipment_name,
        equipment.equipment_type,
        equipment.location_id,
        {{ dbt.date_trunc('month', 'maintenance_logs.completed_date') }} as downtime_month,
        count(*) as maintenance_event_count,
        sum(maintenance_logs.downtime_hours) as total_downtime_hours,
        sum(maintenance_logs.maintenance_cost) as total_maintenance_cost,
        sum(case when maintenance_logs.maintenance_type = 'emergency' then 1 else 0 end) as emergency_count,
        sum(case when maintenance_logs.maintenance_type = 'preventive' then 1 else 0 end) as preventive_count

    from maintenance_logs
    inner join equipment
        on maintenance_logs.equipment_id = equipment.equipment_id
    where maintenance_logs.maintenance_status = 'completed'
    group by
        maintenance_logs.equipment_id,
        equipment.equipment_name,
        equipment.equipment_type,
        equipment.location_id,
        {{ dbt.date_trunc('month', 'maintenance_logs.completed_date') }}

)

select * from monthly_downtime
