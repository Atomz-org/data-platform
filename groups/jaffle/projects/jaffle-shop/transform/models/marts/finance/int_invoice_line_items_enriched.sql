with

invoice_line_items as (

    select * from {{ ref('stg_invoice_line_items') }}

),

products as (

    select * from {{ ref('stg_products') }}

),

enriched as (

    select
        ili.invoice_line_item_id,
        ili.invoice_id,
        ili.product_id,
        p.product_name,
        p.product_type,
        p.is_food_item,
        p.is_drink_item,
        ili.line_item_description,
        ili.quantity,
        ili.unit_price,
        ili.line_total,
        p.product_price as list_price,
        ili.unit_price - p.product_price as price_variance

    from invoice_line_items as ili
    left join products as p
        on ili.product_id = p.product_id

)

select * from enriched
