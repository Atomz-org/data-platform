with

invoices as (

    select * from {{ ref('fct_invoices') }}
    where is_paid = false

),

aged as (

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
        issued_date,
        due_date,
        days_overdue,
        case
            when days_overdue <= 0 then 'current'
            when days_overdue between 1 and 30 then '1-30 days'
            when days_overdue between 31 and 60 then '31-60 days'
            when days_overdue between 61 and 90 then '61-90 days'
            when days_overdue > 90 then '90+ days'
        end as aging_bucket,
        case
            when days_overdue <= 0 then 1
            when days_overdue between 1 and 30 then 2
            when days_overdue between 31 and 60 then 3
            when days_overdue between 61 and 90 then 4
            when days_overdue > 90 then 5
        end as aging_bucket_sort

    from invoices

),

with_summary as (

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
        issued_date,
        due_date,
        days_overdue,
        aging_bucket,
        aging_bucket_sort,
        sum(amount_due) over (
            partition by aging_bucket
        ) as bucket_total_due,
        sum(amount_due) over () as grand_total_due,
        case
            when sum(amount_due) over () > 0
                then amount_due / sum(amount_due) over ()
            else 0
        end as pct_of_total_due,
        count(*) over (
            partition by customer_id
        ) as customer_unpaid_invoice_count

    from aged

)

select * from with_summary
