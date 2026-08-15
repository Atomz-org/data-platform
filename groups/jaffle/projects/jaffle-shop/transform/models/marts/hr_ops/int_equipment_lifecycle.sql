with

equipment as (

    select * from {{ ref('stg_equipment') }}

),

maintenance_logs as (

    select * from {{ ref('stg_maintenance_logs') }}

),

maintenance_summary as (

    select
        equipment_id,
        count(*) as total_maintenance_events,
        sum(maintenance_cost) as total_maintenance_cost,
        sum(downtime_hours) as total_downtime_hours,
        min(scheduled_date) as first_maintenance_date,
        max(completed_date) as last_maintenance_date,
        sum(case when maintenance_type = 'emergency' then 1 else 0 end) as emergency_events,
        sum(case when maintenance_type = 'preventive' then 1 else 0 end) as preventive_events

    from maintenance_logs
    where maintenance_status = 'completed'
    group by equipment_id

),

lifecycle as (

    select
        equipment.equipment_id,
        equipment.location_id,
        equipment.equipment_name,
        equipment.equipment_type,
        equipment.equipment_status,
        equipment.purchase_date,
        equipment.purchase_cost,
        equipment.warranty_expiry_date,
        {{ dbt.datediff('equipment.purchase_date', 'current_date', 'day') }} as age_days,
        {{ dbt.datediff('equipment.purchase_date', 'current_date', 'month') }} as age_months,
        case
            when equipment.warranty_expiry_date >= current_date then true
            else false
        end as is_under_warranty,
        coalesce(maintenance_summary.total_maintenance_events, 0) as total_maintenance_events,
        coalesce(maintenance_summary.total_maintenance_cost, 0) as total_maintenance_cost,
        coalesce(maintenance_summary.total_downtime_hours, 0) as total_downtime_hours,
        coalesce(maintenance_summary.emergency_events, 0) as emergency_events,
        coalesce(maintenance_summary.preventive_events, 0) as preventive_events,
        case
            when {{ dbt.datediff('equipment.purchase_date', 'current_date', 'month') }} > 0
                then round(
                    (coalesce(maintenance_summary.total_maintenance_events, 0) * 12.0
                    / {{ dbt.datediff('equipment.purchase_date', 'current_date', 'month') }}), 1
                )
            else 0
        end as annualized_maintenance_frequency,
        case
            when equipment.purchase_cost > 0
                then round(
                    (coalesce(maintenance_summary.total_maintenance_cost, 0) * 100.0
                    / equipment.purchase_cost), 1
                )
            else 0
        end as maintenance_cost_pct_of_purchase,
        case
            when coalesce(maintenance_summary.total_maintenance_cost, 0)
                > equipment.purchase_cost * 0.5
                then 'high_maintenance_cost'
            when {{ dbt.datediff('equipment.purchase_date', 'current_date', 'month') }} > 60
                then 'aging'
            when equipment.warranty_expiry_date < current_date
                and coalesce(maintenance_summary.emergency_events, 0) > 2
                then 'at_risk'
            else 'healthy'
        end as lifecycle_status

    from equipment
    left join maintenance_summary
        on equipment.equipment_id = maintenance_summary.equipment_id

)

select * from lifecycle
