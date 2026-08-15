with

seasonal_pattern as (

    select
        product_id,
        season_type,
        seasonality_index,
        monthly_quantity
    from {{ ref('int_seasonal_product_index') }}

),

products as (

    select product_id, product_name, product_type
    from {{ ref('stg_products') }}

),

final as (

    select
        sp.product_id,
        p.product_name,
        p.product_type,
        sp.season_type,
        sp.seasonality_index,
        sp.monthly_quantity,
        case
            when sp.seasonality_index > 1.5 then 'strong_seasonal_fit'
            when sp.seasonality_index > 1.1 then 'moderate_seasonal_fit'
            when sp.seasonality_index < 0.5 then 'remove_this_season'
            when sp.seasonality_index < 0.8 then 'weak_this_season'
            else 'year_round'
        end as rotation_recommendation,
        rank() over (
            partition by sp.season_type order by sp.seasonality_index desc
        ) as season_rank
    from seasonal_pattern as sp
    inner join products as p on sp.product_id = p.product_id

)

select * from final
