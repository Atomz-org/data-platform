with

o as (
    select * from {{ ref('stg_orders') }}
),

l as (
    select * from {{ ref('stg_locations') }}
),

invoices as (

    select * from {{ ref('stg_invoices') }}

),

tax_rates as (

    select * from {{ ref('stg_tax_rates') }}

),

order_locations as (

    select
        o.order_id,
        o.location_id,
        l.location_name

    from o
    left join l
        on o.location_id = l.location_id

),

tax_by_jurisdiction as (

    select
        tr.jurisdiction,
        tr.tax_type,
        tr.tax_rate_pct,
        ol.location_id,
        ol.location_name,
        {{ dbt.date_trunc('month', 'inv.issued_date') }} as tax_month,
        count(inv.invoice_id) as invoice_count,
        sum(inv.subtotal) as taxable_amount,
        sum(inv.tax_amount) as tax_collected

    from invoices as inv
    inner join order_locations as ol
        on inv.order_id = ol.order_id
    left join tax_rates as tr
        on inv.issued_date >= tr.effective_from_date
        and (inv.issued_date <= tr.effective_to_date or tr.effective_to_date is null)
    where inv.invoice_status != 'draft'
    group by 1, 2, 3, 4, 5, 6

)

select * from tax_by_jurisdiction
