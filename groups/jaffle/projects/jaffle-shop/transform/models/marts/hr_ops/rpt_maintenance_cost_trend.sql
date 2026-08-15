with

maintenance as (

    select * from {{ ref('fct_maintenance_events') }}

),

monthly_cost as (

    select
        equipment_type,
        location_id,
        location_name,
        {{ dbt.date_trunc('month', 'completed_date') }} as maintenance_month,
        count(*) as event_count,
        sum(maintenance_cost) as total_cost,
        sum(downtime_hours) as total_downtime_hours,
        sum(case when is_emergency then 1 else 0 end) as emergency_events,
        sum(case when is_under_warranty then maintenance_cost else 0 end) as warranty_covered_cost,
        sum(case when not is_under_warranty then maintenance_cost else 0 end) as out_of_pocket_cost,
        round(avg(maintenance_cost), 2) as avg_cost_per_event

    from maintenance
    where maintenance_status = 'completed'
        and completed_date is not null
    group by
        equipment_type,
        location_id,
        location_name,
        {{ dbt.date_trunc('month', 'completed_date') }}

),

with_trend as (

    select
        equipment_type,
        location_id,
        location_name,
        maintenance_month,
        event_count,
        total_cost,
        total_downtime_hours,
        emergency_events,
        warranty_covered_cost,
        out_of_pocket_cost,
        avg_cost_per_event,
        lag(total_cost) over (
            partition by equipment_type, location_id
            order by maintenance_month
        ) as prev_month_cost,
        case
            when lag(total_cost) over (
                partition by equipment_type, location_id
                order by maintenance_month
            ) > 0
                then round(
                    (total_cost - lag(total_cost) over (
                        partition by equipment_type, location_id
                        order by maintenance_month
                    )) * 100.0
                    / lag(total_cost) over (
                        partition by equipment_type, location_id
                        order by maintenance_month
                    ), 1
                )
            else null
        end as cost_change_pct,
        avg(total_cost) over (
            partition by equipment_type, location_id
            order by maintenance_month
            rows between 2 preceding and current row
        ) as rolling_3mo_avg_cost

    from monthly_cost

)

select * from with_trend
