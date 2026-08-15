with

source as (

    select * from {{ source('product', 'raw_pricing_history') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as pricing_history_id,
        cast(product_id as varchar) as product_id,

        ---------- numerics
        {{ cents_to_dollars('old_price') }} as old_price,
        {{ cents_to_dollars('new_price') }} as new_price,

        ---------- text
        change_reason,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'changed_at') }} as price_changed_date

    from source

)

select * from renamed
