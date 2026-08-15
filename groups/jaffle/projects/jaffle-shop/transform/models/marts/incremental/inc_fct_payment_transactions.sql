{{
    config(
        materialized='incremental',
        unique_key='payment_transaction_id'
    )
}}

with

payments as (

    select * from {{ ref('stg_payment_transactions') }}
    {% if is_incremental() %}
    where processed_date > (select max(processed_date) from {{ this }})
    {% endif %}

)

select
    payment_transaction_id,
    order_id,
    gift_card_id,
    payment_method,
    payment_status,
    reference_number,
    payment_amount,
    processed_date,
    {{ dbt.date_trunc('month', 'processed_date') }} as payment_month

from payments
