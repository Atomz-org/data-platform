with

invoices as (
    select * from {{ ref('fct_invoices') }}
),

customers as (
    select * from {{ ref('stg_customers') }}
),

locations as (
    select * from {{ ref('stg_locations') }}
),

invoice_lines as (
    select * from {{ ref('stg_invoice_line_items') }}
),

payments as (
    select
        order_id,
        sum(payment_amount) as total_paid,
        count(*) as payment_count,
        max(processed_date) as last_payment_date
    from {{ ref('stg_payment_transactions') }}
    where payment_status = 'completed'
    group by order_id
)

select
    i.invoice_id,
    i.customer_id,
    c.customer_name,
    i.location_id,
    l.location_name,
    i.issued_date,
    i.due_date,
    i.total_amount,
    i.tax_amount,
    i.invoice_status,
    count(distinct il.invoice_line_item_id) as line_item_count,
    p.total_paid,
    p.payment_count,
    p.last_payment_date,
    i.total_amount - coalesce(p.total_paid, 0) as outstanding_balance

from invoices as i
left join customers as c on i.customer_id = c.customer_id
left join locations as l on i.location_id = l.location_id
left join invoice_lines as il on i.invoice_id = il.invoice_id
left join payments as p on i.order_id = p.order_id
group by
    i.invoice_id, i.customer_id, c.customer_name, i.location_id, l.location_name,
    i.issued_date, i.due_date, i.total_amount, i.tax_amount, i.invoice_status,
    p.total_paid, p.payment_count, p.last_payment_date
