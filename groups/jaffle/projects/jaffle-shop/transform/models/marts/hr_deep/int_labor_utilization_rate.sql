with

timecards as (

    select
        location_id,
        work_date,
        sum(hours_worked) as total_clocked_hours
    from {{ ref('stg_timecards') }}
    where timecard_status = 'approved'
    group by 1, 2

),

order_activity as (

    select
        location_id,
        ordered_at as order_date,
        count(order_id) as order_count
    from {{ ref('stg_orders') }}
    group by 1, 2

),

final as (

    select
        t.location_id,
        t.work_date,
        t.total_clocked_hours,
        coalesce(oa.order_count, 0) as order_count,
        case
            when coalesce(oa.order_count, 0) > 0 and t.total_clocked_hours > 0
                then round(cast(oa.order_count * 1.0 / t.total_clocked_hours as {{ dbt.type_float() }}), 2)
            else 0
        end as orders_per_labor_hour,
        case
            when t.total_clocked_hours > 0 and coalesce(oa.order_count, 0) = 0
                then 'idle'
            when t.total_clocked_hours > 0 and oa.order_count * 1.0 / t.total_clocked_hours < 2
                then 'low_utilization'
            when t.total_clocked_hours > 0 and oa.order_count * 1.0 / t.total_clocked_hours < 5
                then 'moderate_utilization'
            else 'high_utilization'
        end as utilization_tier
    from timecards as t
    left join order_activity as oa
        on t.location_id = oa.location_id
        and t.work_date = oa.order_date

)

select * from final
