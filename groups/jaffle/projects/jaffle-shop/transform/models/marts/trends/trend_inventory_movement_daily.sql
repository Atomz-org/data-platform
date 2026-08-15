with

daily_inventory as (
    select
        moved_at,
        location_id,
        sum(case when movement_type = 'inbound' then quantity else 0 end) as inbound_qty,
        sum(case when movement_type = 'outbound' then quantity else 0 end) as outbound_qty,
        sum(absolute_quantity) as total_absolute_quantity
    from {{ ref('fct_inventory_movements') }}
    group by 1, 2
),

trended as (
    select
        moved_at,
        location_id,
        inbound_qty,
        outbound_qty,
        total_absolute_quantity,
        avg(inbound_qty) over (
            partition by location_id order by moved_at
            rows between 6 preceding and current row
        ) as inbound_7d_ma,
        avg(outbound_qty) over (
            partition by location_id order by moved_at
            rows between 6 preceding and current row
        ) as outbound_7d_ma,
        inbound_qty - outbound_qty as net_movement,
        avg(inbound_qty - outbound_qty) over (
            partition by location_id order by moved_at
            rows between 6 preceding and current row
        ) as net_movement_7d_ma
    from daily_inventory
)

select * from trended
