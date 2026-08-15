with

orders as (

    select * from {{ ref('stg_orders') }}

),

invoices as (

    select
        order_id
    from {{ ref('fct_invoices') }}

),

missing as (

    select
        o.order_id,
        o.customer_id,
        o.location_id,
        o.ordered_at,
        o.order_total,
        'completed',
        case
            when 'completed' = 'completed' then 'completed_no_invoice'
            when 'completed' = 'pending' then 'pending_no_invoice'
            else 'other_no_invoice'
        end as missing_invoice_type

    from orders as o

    left join invoices as inv
        on o.order_id = inv.order_id

    where inv.order_id is null

)

select * from missing
