with 
il as (
    select * from {{ ref('int_inventory_current_level') }}
),

p as (
    select * from {{ ref('stg_products') }}
),

current_inventory as (
    select
        il.location_id as store_id,
        il.product_id,
        il.current_quantity,
        coalesce(p.product_price, 0) as unit_price,
        il.current_quantity * coalesce(p.product_price, 0) as inventory_value
    from il
    left join p on il.product_id = p.product_id
),

store_inventory_summary as (
    select
        store_id,
        count(distinct product_id) as distinct_products_stocked,
        sum(current_quantity) as total_units_on_hand,
        sum(inventory_value) as total_inventory_value,
        avg(inventory_value) as avg_inventory_value_per_product,
        max(inventory_value) as max_product_inventory_value
    from current_inventory
    group by store_id
)

select
    store_id,
    distinct_products_stocked,
    total_units_on_hand,
    total_inventory_value,
    round(avg_inventory_value_per_product, 2) as avg_inventory_value_per_product,
    max_product_inventory_value,
    round(total_inventory_value * 0.02, 2) as estimated_monthly_holding_cost,
    round(total_inventory_value * 0.24, 2) as estimated_annual_holding_cost
from store_inventory_summary
