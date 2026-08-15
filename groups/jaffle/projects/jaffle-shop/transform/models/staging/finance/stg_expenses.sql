with

source as (

    select * from {{ source('finance', 'raw_expenses') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as expense_id,
        cast(store_id as varchar) as location_id,
        cast(category_id as varchar) as expense_category_id,

        ---------- text
        description as expense_description,
        vendor,

        ---------- numerics
        {{ cents_to_dollars('amount') }} as expense_amount,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'incurred_at') }} as incurred_date

    from source

)

select * from renamed
