with

product_sales_daily as (

    select * from {{ ref('int_product_sales_daily') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

order_items as (

    select * from {{ ref('stg_order_items') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

order_location as (

    select
        oi.product_id,
        o.ordered_at as sale_date,
        o.location_id

    from order_items as oi
    inner join orders as o
        on oi.order_id = o.order_id

),

sales_by_location as (

    select
        ol.location_id,
        l.location_name,
        psd.sale_date,
        psd.product_id,
        psd.product_name,
        psd.product_type,
        count(ol.product_id) as units_sold,
        count(ol.product_id) * psd.current_unit_price as daily_revenue

    from product_sales_daily as psd
    inner join order_location as ol
        on psd.product_id = ol.product_id
        and psd.sale_date = ol.sale_date
    inner join locations as l
        on ol.location_id = l.location_id
    group by
        ol.location_id,
        l.location_name,
        psd.sale_date,
        psd.product_id,
        psd.product_name,
        psd.product_type,
        psd.current_unit_price

)

select * from sales_by_location
