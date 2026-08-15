with

daily_maintenance as (
    select
        completed_date,
        location_id,
        count(*) as maintenance_events,
        sum(maintenance_cost) as total_cost
    from {{ ref('fct_maintenance_events') }}
    group by 1, 2
),

trended as (
    select
        completed_date,
        location_id,
        maintenance_events,
        total_cost,
        avg(maintenance_events) over (
            partition by location_id order by completed_date
            rows between 27 preceding and current row
        ) as events_28d_ma,
        avg(total_cost) over (
            partition by location_id order by completed_date
            rows between 27 preceding and current row
        ) as cost_28d_ma,
        sum(maintenance_events) over (
            partition by location_id order by completed_date
            rows between 89 preceding and current row
        ) as events_90d_total,
        case
            when maintenance_events > 3 * avg(maintenance_events) over (
                partition by location_id order by completed_date
                rows between 27 preceding and current row
            ) then 'equipment_concern'
            else 'normal'
        end as maintenance_alert
    from daily_maintenance
)

select * from trended
