with

source as (

    select * from {{ source('ecom', 'raw_items') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as order_item_id,
        cast(order_id as varchar) as order_id,
        cast(sku as varchar) as product_id

    from source

)

select * from renamed
