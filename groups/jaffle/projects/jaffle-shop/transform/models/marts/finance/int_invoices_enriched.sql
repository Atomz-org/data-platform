with

invoices as (

    select * from {{ ref('stg_invoices') }}

),

orders as (

    select * from {{ ref('stg_orders') }}

),

customers as (

    select * from {{ ref('stg_customers') }}

),

enriched as (

    select
        inv.invoice_id,
        inv.order_id,
        inv.customer_id,
        c.customer_name,
        o.location_id,
        inv.invoice_status,
        inv.subtotal,
        inv.tax_amount,
        inv.total_amount,
        inv.amount_paid,
        inv.amount_due,
        o.subtotal as order_subtotal,
        o.tax_paid as order_tax_paid,
        o.order_total,
        inv.issued_date,
        inv.due_date,
        inv.paid_date,
        o.ordered_at as order_date,
        case
            when inv.paid_date is not null
                then {{ sf_datediff('day', "inv.issued_date", "inv.paid_date") }}
            else null
        end as days_to_payment,
        case
            when inv.invoice_status = 'overdue'
                then {{ sf_datediff('day', "inv.due_date", "current_date") }}
            else 0
        end as days_overdue

    from invoices as inv
    left join orders as o
        on inv.order_id = o.order_id
    left join customers as c
        on inv.customer_id = c.customer_id

)

select * from enriched
