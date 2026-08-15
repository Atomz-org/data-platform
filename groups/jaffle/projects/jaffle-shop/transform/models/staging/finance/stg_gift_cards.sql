with

source as (

    select * from {{ source('finance', 'raw_gift_cards') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as gift_card_id,
        cast(customer_id as varchar) as customer_id,

        ---------- text
        card_number,
        status as gift_card_status,

        ---------- numerics
        {{ cents_to_dollars('initial_balance') }} as initial_balance,
        {{ cents_to_dollars('current_balance') }} as current_balance,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'issued_at') }} as issued_date,
        {{ dbt.date_trunc('day', 'expires_at') }} as expires_date

    from source

)

select * from renamed
