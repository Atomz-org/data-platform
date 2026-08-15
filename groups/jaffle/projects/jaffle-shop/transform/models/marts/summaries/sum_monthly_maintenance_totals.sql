with final as (
    select
        {{ sf_date_trunc('month', "completed_date") }} as maint_month,
        location_id,
        count(*) as event_count,
        sum(maintenance_cost) as total_cost,
        round(avg(maintenance_cost), 2) as avg_cost_per_event,
        count(distinct equipment_id) as unique_equipment
    from {{ ref('fct_maintenance_events') }}
    group by 1, 2
)
select * from final
