with

payments as (

    select
        payment_transaction_id,
        order_id,
        payment_amount,
        payment_status,
        payment_method,
        processed_date
    from {{ ref('stg_payment_transactions') }}

),

invoices as (

    select
        invoice_id,
        order_id,
        total_amount,
        invoice_status,
        issued_date
    from {{ ref('fct_invoices') }}

),

matched as (

    select
        p.payment_transaction_id,
        p.order_id,
        p.payment_amount,
        p.payment_status,
        p.payment_method,
        p.processed_date,
        i.invoice_id,
        i.total_amount,
        i.invoice_status,
        i.issued_date,
        case
            when i.invoice_id is null then 'payment_no_invoice'
            when abs(p.payment_amount - i.total_amount) < 0.01 then 'matched'
            when p.payment_amount < i.total_amount then 'underpayment'
            when p.payment_amount > i.total_amount then 'overpayment'
            else 'unreconciled'
        end as reconciliation_status,
        coalesce(p.payment_amount - i.total_amount, p.payment_amount) as variance_amount
    from payments as p
    left join invoices as i
        on p.order_id = i.order_id

)

select
    payment_transaction_id,
    order_id,
    payment_amount,
    payment_status,
    payment_method,
    processed_date,
    invoice_id,
    total_amount,
    invoice_status,
    reconciliation_status,
    variance_amount
from matched
