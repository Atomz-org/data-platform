with

source as (

    select * from {{ source('marketing', 'raw_loyalty_transactions') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as loyalty_transaction_id,
        cast(loyalty_member_id as varchar) as loyalty_member_id,
        cast(order_id as varchar) as order_id,

        ---------- text
        transaction_type,
        description as transaction_description,

        ---------- numerics
        points,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'transacted_at') }} as transacted_at

    from source

)

select * from renamed
