with

maintenance_events as (

    select * from {{ ref('fct_maintenance_events') }}

),

equipment as (

    select * from {{ ref('dim_equipment') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

)

select
    me.maintenance_log_id,
    me.equipment_id,
    eq.equipment_name,
    eq.equipment_type,
    me.location_id,
    l.location_name as store_name,
    me.scheduled_date,
    me.maintenance_type,
    me.maintenance_cost as maintenance_cost,
    me.downtime_hours,
    me.maintenance_description,
    case
        when me.maintenance_type = 'emergency' then 'unplanned'
        else 'planned'
    end as maintenance_category,
    round(me.maintenance_cost / nullif(me.downtime_hours, 0), 2) as cost_per_downtime_hour

from maintenance_events me
left join equipment eq on me.equipment_id = eq.equipment_id
left join locations l on me.location_id = l.location_id
