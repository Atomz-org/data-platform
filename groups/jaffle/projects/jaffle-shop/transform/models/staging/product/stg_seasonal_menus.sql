with

source as (

    select * from {{ source('product', 'raw_seasonal_menus') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as seasonal_menu_id,
        cast(menu_item_id as varchar) as menu_item_id,

        ---------- text
        season_name,
        promotion_name,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'start_date') }} as promotion_start_date,
        {{ dbt.date_trunc('day', 'end_date') }} as promotion_end_date,

        ---------- booleans
        coalesce(is_active, false) as is_active_promotion

    from source

)

select * from renamed
