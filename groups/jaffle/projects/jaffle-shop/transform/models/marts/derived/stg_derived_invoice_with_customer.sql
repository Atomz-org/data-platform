with

invoices as (
    select * from {{ ref('stg_invoices') }}
),

customers as (
    select customer_id, customer_name from {{ ref('stg_customers') }}
),

final as (
    select
        i.invoice_id,
        i.customer_id,
        c.customer_name,
        i.issued_date,
        i.due_date,
        i.total_amount,
        i.invoice_status
    from invoices as i
    left join customers as c on i.customer_id = c.customer_id
)

select * from final
