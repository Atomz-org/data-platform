with

source as (

    select * from {{ source('finance', 'raw_payment_transactions') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as payment_transaction_id,
        cast(order_id as varchar) as order_id,
        cast(gift_card_id as varchar) as gift_card_id,

        ---------- text
        payment_method,
        status as payment_status,
        reference_number,

        ---------- numerics
        {{ cents_to_dollars('amount') }} as payment_amount,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'processed_at') }} as processed_date

    from source

)

select * from renamed
