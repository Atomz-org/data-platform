with

source as (

    select * from {{ source('product', 'raw_product_reviews') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as review_id,
        cast(product_id as varchar) as product_id,
        cast(customer_id as varchar) as customer_id,
        cast(order_id as varchar) as order_id,

        ---------- numerics
        rating,

        ---------- text
        review_title,
        review_body,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'reviewed_at') }} as reviewed_date

    from source

)

select * from renamed
