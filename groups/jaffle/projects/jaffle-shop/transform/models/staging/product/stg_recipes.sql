with

source as (

    select * from {{ source('product', 'raw_recipes') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as recipe_id,
        cast(menu_item_id as varchar) as menu_item_id,

        ---------- text
        name as recipe_name,
        description as recipe_description,

        ---------- numerics
        serving_size,

        ---------- booleans
        coalesce(is_active, false) as is_active_recipe,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'created_at') }} as created_date,
        {{ dbt.date_trunc('day', 'updated_at') }} as updated_date

    from source

)

select * from renamed
