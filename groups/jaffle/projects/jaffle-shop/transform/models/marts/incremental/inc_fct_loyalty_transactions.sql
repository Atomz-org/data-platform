{{
    config(
        materialized='incremental',
        unique_key='loyalty_transaction_id'
    )
}}

with

loyalty_txns as (

    select * from {{ ref('stg_loyalty_transactions') }}
    {% if is_incremental() %}
    where transacted_at > (select max(transacted_at) from {{ this }})
    {% endif %}

)

select
    loyalty_transaction_id,
    loyalty_member_id,
    transaction_type,
    points,
    transacted_at,
    order_id,
    {{ dbt.date_trunc('month', 'transacted_at') }} as transaction_month

from loyalty_txns
