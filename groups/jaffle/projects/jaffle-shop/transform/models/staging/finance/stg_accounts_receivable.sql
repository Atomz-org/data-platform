with

source as (

    select * from {{ source('finance', 'raw_accounts_receivable') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as receivable_id,
        cast(customer_id as varchar) as customer_id,
        cast(invoice_id as varchar) as invoice_id,

        ---------- text
        status as receivable_status,

        ---------- numerics
        {{ cents_to_dollars('amount_due') }} as amount_due,
        {{ cents_to_dollars('amount_paid') }} as amount_paid,
        {{ cents_to_dollars('amount_outstanding') }} as amount_outstanding,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'due_at') }} as due_date,
        {{ dbt.date_trunc('day', 'created_at') }} as created_date

    from source

)

select * from renamed
