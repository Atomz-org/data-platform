with

source as (

    select * from {{ source('product', 'raw_ingredient_prices') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as ingredient_price_id,
        cast(ingredient_id as varchar) as ingredient_id,
        cast(supplier_id as varchar) as supplier_id,

        ---------- numerics
        {{ cents_to_dollars('unit_cost') }} as unit_cost,
        quantity as minimum_order_quantity,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'effective_from') }} as effective_from_date,
        {{ dbt.date_trunc('day', 'effective_to') }} as effective_to_date

    from source

)

select * from renamed
