with

source as (

    select * from {{ source('product', 'raw_ingredients') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as ingredient_id,

        ---------- text
        name as ingredient_name,
        category as ingredient_category,
        unit as default_unit,

        ---------- booleans
        coalesce(is_perishable, false) as is_perishable,
        coalesce(is_allergen, false) as is_allergen

    from source

)

select * from renamed
