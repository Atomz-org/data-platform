with

order_items as (

    select * from {{ ref('stg_order_items') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

supplies as (

    select * from {{ ref('stg_supplies') }}

),

weekly_demand as (

    select
        supplies.product_id,
        supplies.supply_id,
        supplies.supply_name,
        {{ dbt.date_trunc('week', 'orders.ordered_at') }} as demand_week,
        count(order_items.order_item_id) as units_ordered,
        sum(supplies.supply_cost) as total_ingredient_cost

    from order_items

    inner join orders
        on order_items.order_id = orders.order_id

    inner join supplies
        on order_items.product_id = supplies.product_id

    group by
        supplies.product_id,
        supplies.supply_id,
        supplies.supply_name,
        {{ dbt.date_trunc('week', 'orders.ordered_at') }}

),

with_moving_avg as (

    select
        product_id,
        supply_id,
        supply_name,
        demand_week,
        units_ordered,
        total_ingredient_cost,
        avg(units_ordered) over (
            partition by product_id, supply_id
            order by demand_week
            rows between 3 preceding and current row
        ) as forecast_units_4wk_avg,
        avg(total_ingredient_cost) over (
            partition by product_id, supply_id
            order by demand_week
            rows between 3 preceding and current row
        ) as forecast_cost_4wk_avg

    from weekly_demand

)

select * from with_moving_avg
