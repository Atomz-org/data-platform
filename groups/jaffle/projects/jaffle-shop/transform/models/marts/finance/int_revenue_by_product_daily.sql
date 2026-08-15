with

line_items as (

    select * from {{ ref('stg_invoice_line_items') }}

),

invoices as (

    select
        invoice_id,
        issued_date,
        invoice_status

    from {{ ref('stg_invoices') }}
    where invoice_status != 'draft'

),

products as (

    select * from {{ ref('stg_products') }}

),

product_daily as (

    select
        inv.issued_date as revenue_date,
        li.product_id,
        p.product_name,
        p.product_type,
        count(distinct inv.invoice_id) as invoice_count,
        sum(li.quantity) as units_sold,
        sum(li.line_total) as product_revenue,
        avg(li.unit_price) as avg_unit_price,
        avg(li.line_total) as avg_line_total,
        sum(li.line_total) / nullif(sum(li.quantity), 0) as revenue_per_unit

    from line_items as li
    inner join invoices as inv
        on li.invoice_id = inv.invoice_id
    left join products as p
        on li.product_id = p.product_id
    group by 1, 2, 3, 4

)

select * from product_daily
