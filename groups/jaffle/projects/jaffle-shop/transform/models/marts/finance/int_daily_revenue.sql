with

invoices as (

    select * from {{ ref('stg_invoices') }}

),

locations as (

    select * from {{ ref('stg_locations') }}

),

daily_agg as (

    select
        inv.issued_date as revenue_date,
        l.location_id,
        l.location_name,
        count(inv.invoice_id) as invoice_count,
        sum(inv.subtotal) as gross_revenue,
        sum(inv.tax_amount) as tax_collected,
        sum(inv.total_amount) as total_revenue,
        avg(inv.total_amount) as avg_invoice_amount

    from invoices as inv
    inner join (
        select distinct
            order_id,
            location_id
        from {{ ref('stg_orders') }}
    ) as order_locations
        on inv.order_id = order_locations.order_id
    left join locations as l
        on order_locations.location_id = l.location_id
    where inv.invoice_status != 'draft'
    group by 1, 2, 3

)

select * from daily_agg
