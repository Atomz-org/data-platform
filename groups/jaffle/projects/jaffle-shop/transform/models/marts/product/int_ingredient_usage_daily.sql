with

order_items as (

    select * from {{ ref('stg_order_items') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

recipes as (

    select * from {{ ref('stg_recipes') }}

),

recipe_ingredients as (

    select * from {{ ref('stg_recipe_ingredients') }}

),

menu_items as (

    select * from {{ ref('stg_menu_items') }}

),

order_items_with_date as (

    select
        oi.order_item_id,
        oi.product_id,
        o.ordered_at as order_date

    from order_items as oi
    inner join orders as o
        on oi.order_id = o.order_id

),

product_to_recipe as (

    select
        mi.product_id,
        r.recipe_id

    from menu_items as mi
    inner join recipes as r
        on mi.menu_item_id = r.menu_item_id
        and r.is_active_recipe = true

),

daily_usage as (

    select
        oid.order_date,
        ri.ingredient_id,
        ri.quantity_unit,
        sum(ri.quantity) as total_quantity_used,
        count(distinct oid.order_item_id) as order_item_count

    from order_items_with_date as oid
    inner join product_to_recipe as ptr
        on oid.product_id = ptr.product_id
    inner join recipe_ingredients as ri
        on ptr.recipe_id = ri.recipe_id
    group by oid.order_date, ri.ingredient_id, ri.quantity_unit

)

select * from daily_usage
