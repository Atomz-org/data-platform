with

movements as (

    select * from {{ ref('stg_inventory_movements') }}

),

warehouses as (

    select
        warehouse_id,
        warehouse_name
    from {{ ref('stg_warehouses') }}

),

daily_throughput as (

    select
        m.location_id as warehouse_id,
        m.moved_at as throughput_date,
        sum(case when m.movement_type = 'inbound' then abs(m.quantity) else 0 end) as inbound_units,
        sum(case when m.movement_type = 'outbound' then abs(m.quantity) else 0 end) as outbound_units,
        sum(abs(m.quantity)) as total_units_moved,
        count(distinct m.product_id) as distinct_products,
        count(m.movement_id) as movement_events
    from movements as m
    group by 1, 2

),

final as (

    select
        dt.warehouse_id,
        w.warehouse_name,
        dt.throughput_date,
        dt.inbound_units,
        dt.outbound_units,
        dt.total_units_moved,
        dt.distinct_products,
        dt.movement_events,
        dt.outbound_units - dt.inbound_units as net_flow
    from daily_throughput as dt
    left join warehouses as w
        on dt.warehouse_id = w.warehouse_id

)

select * from final
