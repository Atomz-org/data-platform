with

source as (

    select * from {{ source('finance', 'raw_refunds') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as refund_id,
        cast(order_id as varchar) as order_id,
        cast(invoice_id as varchar) as invoice_id,

        ---------- text
        reason as refund_reason,
        status as refund_status,

        ---------- numerics
        {{ cents_to_dollars('refund_amount') }} as refund_amount,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'requested_at') }} as requested_date,
        {{ dbt.date_trunc('day', 'resolved_at') }} as resolved_date

    from source

)

select * from renamed
