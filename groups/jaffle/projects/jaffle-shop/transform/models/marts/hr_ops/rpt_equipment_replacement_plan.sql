with

lifecycle as (

    select * from {{ ref('int_equipment_lifecycle') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

replacement_candidates as (

    select
        lifecycle.equipment_id,
        lifecycle.location_id,
        locations.location_name,
        lifecycle.equipment_name,
        lifecycle.equipment_type,
        lifecycle.equipment_status,
        lifecycle.purchase_date,
        lifecycle.purchase_cost,
        lifecycle.warranty_expiry_date,
        lifecycle.is_under_warranty,
        lifecycle.age_days,
        lifecycle.age_months,
        lifecycle.total_maintenance_events,
        lifecycle.total_maintenance_cost,
        lifecycle.total_downtime_hours,
        lifecycle.emergency_events,
        lifecycle.annualized_maintenance_frequency,
        lifecycle.maintenance_cost_pct_of_purchase,
        lifecycle.lifecycle_status,
        case
            when lifecycle.lifecycle_status = 'high_maintenance_cost' then 1
            when lifecycle.lifecycle_status = 'at_risk' then 2
            when lifecycle.lifecycle_status = 'aging' then 3
            else 4
        end as replacement_priority,
        case
            when lifecycle.lifecycle_status = 'high_maintenance_cost'
                then 'Maintenance cost exceeds 50% of purchase price'
            when lifecycle.lifecycle_status = 'at_risk'
                then 'Out of warranty with multiple emergency repairs'
            when lifecycle.lifecycle_status = 'aging'
                then 'Equipment older than 5 years'
            else 'No immediate replacement needed'
        end as replacement_reason,
        lifecycle.purchase_cost + lifecycle.total_maintenance_cost as total_cost_of_ownership,
        case
            when lifecycle.age_months > 0
                then round(
                    (lifecycle.purchase_cost + lifecycle.total_maintenance_cost) * 1.0
                    / lifecycle.age_months, 2
                )
            else null
        end as monthly_cost_of_ownership

    from lifecycle
    left join locations
        on lifecycle.location_id = locations.location_id

),

final as (

    select
        equipment_id,
        location_id,
        location_name,
        equipment_name,
        equipment_type,
        equipment_status,
        purchase_date,
        purchase_cost,
        warranty_expiry_date,
        is_under_warranty,
        age_months,
        total_maintenance_events,
        total_maintenance_cost,
        total_downtime_hours,
        emergency_events,
        annualized_maintenance_frequency,
        maintenance_cost_pct_of_purchase,
        lifecycle_status,
        replacement_priority,
        replacement_reason,
        total_cost_of_ownership,
        monthly_cost_of_ownership

    from replacement_candidates
    where lifecycle_status != 'healthy'

)

select * from final
