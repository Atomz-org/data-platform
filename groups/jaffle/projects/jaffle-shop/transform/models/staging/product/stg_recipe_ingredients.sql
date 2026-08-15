with

source as (

    select * from {{ source('product', 'raw_recipe_ingredients') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as recipe_ingredient_id,
        cast(recipe_id as varchar) as recipe_id,
        cast(ingredient_id as varchar) as ingredient_id,

        ---------- numerics
        quantity,
        unit as quantity_unit

    from source

)

select * from renamed
