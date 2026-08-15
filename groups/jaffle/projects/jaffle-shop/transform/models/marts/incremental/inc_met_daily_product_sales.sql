{{
    config(
        materialized='incremental',
        unique_key='product_sales_key'
    )
}}

with

order_items as (

    select * from {{ ref('stg_order_items') }}

),

orders as (

    select order_id, ordered_at, location_id from {{ ref('stg_orders') }}
    {% if is_incremental() %}
    where ordered_at > (select max(sale_date) from {{ this }})
    {% endif %}

),

supplies_by_product as (

    select product_id, sum(supply_cost) as supply_cost
    from {{ ref('stg_supplies') }}
    group by product_id

),

daily_product as (

    select
        o.location_id as store_id,
        oi.product_id,
        {{ dbt.date_trunc('day', 'o.ordered_at') }} as sale_date,
        count(oi.order_item_id) as total_quantity,
        sum(coalesce(s.supply_cost, 0)) as total_cost,
        count(distinct o.order_id) as order_count

    from order_items oi
    inner join orders o on oi.order_id = o.order_id
    left join supplies_by_product s on oi.product_id = s.product_id
    group by o.location_id, oi.product_id, {{ dbt.date_trunc('day', 'o.ordered_at') }}

)

select
    store_id || '-' || product_id || '-' || cast(sale_date as varchar) as product_sales_key,
    store_id,
    product_id,
    sale_date,
    total_quantity,
    total_cost,
    order_count

from daily_product
