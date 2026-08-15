with

source as (

    select * from {{ source('finance', 'raw_invoices') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as invoice_id,
        cast(order_id as varchar) as order_id,
        cast(customer_id as varchar) as customer_id,

        ---------- text
        status as invoice_status,

        ---------- numerics
        {{ cents_to_dollars('subtotal') }} as subtotal,
        {{ cents_to_dollars('tax_amount') }} as tax_amount,
        {{ cents_to_dollars('total_amount') }} as total_amount,
        {{ cents_to_dollars('amount_paid') }} as amount_paid,
        {{ cents_to_dollars('amount_due') }} as amount_due,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'issued_at') }} as issued_date,
        {{ dbt.date_trunc('day', 'due_at') }} as due_date,
        {{ dbt.date_trunc('day', 'paid_at') }} as paid_date

    from source

)

select * from renamed
