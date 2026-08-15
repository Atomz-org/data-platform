with

inventory_value as (

    select * from {{ ref('int_inventory_value_by_location') }}

),

products as (

    select * from {{ ref('stg_products') }}

),

warehouses as (

    select * from {{ ref('dim_warehouses') }}

),

value_by_warehouse_product as (

    select
        warehouses.warehouse_id,
        warehouses.warehouse_name,
        products.product_id,
        products.product_name,
        products.product_type,
        sum(inventory_value.current_quantity) as total_quantity,
        sum(inventory_value.inventory_value) as total_value,
        avg(inventory_value.unit_cost) as avg_unit_cost

    from inventory_value

    left join warehouses
        on inventory_value.location_id = warehouses.warehouse_id

    left join products
        on inventory_value.product_id = products.product_id

    group by
        warehouses.warehouse_id,
        warehouses.warehouse_name,
        products.product_id,
        products.product_name,
        products.product_type

),

summary as (

    select
        *,
        sum(total_value) over (
            partition by warehouse_id
        ) as warehouse_total_value,
        case
            when sum(total_value) over (partition by warehouse_id) > 0
                then total_value * 1.0
                    / sum(total_value) over (partition by warehouse_id)
            else 0
        end as value_share_of_warehouse

    from value_by_warehouse_product

)

select * from summary
