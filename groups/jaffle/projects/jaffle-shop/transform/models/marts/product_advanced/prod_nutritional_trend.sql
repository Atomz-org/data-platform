with

oi as (
    select * from {{ ref('stg_order_items') }}
),

order_items as (

    select oi.order_id, oi.product_id, 1 as quantity
    from oi

),

orders as (

    select order_id, {{ dbt.date_trunc('month', 'ordered_at') }} as order_month
    from {{ ref('stg_orders') }}

),

nutrition as (

    select
        menu_item_id as product_id,
        calories,
        total_fat_g,
        protein_g,
        total_carbs_g
    from {{ ref('stg_nutritional_info') }}

),

monthly as (

    select
        o.order_month,
        sum(oi.quantity * n.calories) / nullif(sum(oi.quantity), 0) as avg_calories_per_item,
        sum(oi.quantity * n.total_fat_g) / nullif(sum(oi.quantity), 0) as avg_fat_per_item,
        sum(oi.quantity * n.protein_g) / nullif(sum(oi.quantity), 0) as avg_protein_per_item,
        sum(oi.quantity * n.total_carbs_g) / nullif(sum(oi.quantity), 0) as avg_carbs_per_item,
        sum(oi.quantity) as total_items_sold
    from order_items as oi
    inner join orders as o on oi.order_id = o.order_id
    inner join nutrition as n on oi.product_id = n.product_id
    group by 1

),

final as (

    select
        order_month,
        avg_calories_per_item,
        avg_fat_per_item,
        avg_protein_per_item,
        avg_carbs_per_item,
        total_items_sold,
        lag(avg_calories_per_item) over (order by order_month) as prev_month_calories,
        avg_calories_per_item - coalesce(lag(avg_calories_per_item) over (order by order_month), avg_calories_per_item) as calorie_trend
    from monthly

)

select * from final
