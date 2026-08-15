with

invoices_enriched as (

    select * from {{ ref('int_invoices_enriched') }}

),

final as (

    select
        invoice_id,
        order_id,
        customer_id,
        customer_name,
        location_id,
        invoice_status,
        subtotal,
        tax_amount,
        total_amount,
        amount_paid,
        amount_due,
        order_subtotal,
        order_tax_paid,
        order_total,
        issued_date,
        due_date,
        paid_date,
        order_date,
        days_to_payment,
        days_overdue,
        case
            when invoice_status = 'paid' then true
            else false
        end as is_paid,
        case
            when invoice_status = 'overdue' then true
            else false
        end as is_overdue

    from invoices_enriched

)

select * from final
