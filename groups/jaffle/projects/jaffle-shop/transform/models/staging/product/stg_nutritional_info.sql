with

source as (

    select * from {{ source('product', 'raw_nutritional_info') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as nutritional_info_id,
        cast(menu_item_id as varchar) as menu_item_id,

        ---------- numerics
        calories,
        total_fat_g,
        saturated_fat_g,
        trans_fat_g,
        cholesterol_mg,
        sodium_mg,
        total_carbs_g,
        dietary_fiber_g,
        total_sugars_g,
        protein_g,
        caffeine_mg,

        ---------- text
        serving_size_description,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'updated_at') }} as updated_date

    from source

)

select * from renamed
