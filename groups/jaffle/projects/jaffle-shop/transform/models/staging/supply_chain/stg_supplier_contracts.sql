with

source as (

    select * from {{ source('supply_chain', 'raw_supplier_contracts') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as contract_id,
        cast(supplier_id as varchar) as supplier_id,

        ---------- text
        contract_type,
        payment_terms,

        ---------- numerics
        {{ cents_to_dollars('minimum_order_amount') }} as minimum_order_amount,
        lead_time_days,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'effective_date') }} as effective_date,
        {{ dbt.date_trunc('day', 'expiration_date') }} as expiration_date,
        {{ dbt.date_trunc('day', 'created_at') }} as created_at

    from source

)

select * from renamed
