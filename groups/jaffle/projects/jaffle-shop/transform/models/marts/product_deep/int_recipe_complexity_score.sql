with

recipe_ingredients as (

    select * from {{ ref('stg_recipe_ingredients') }}

),

recipe_stats as (

    select
        recipe_id,
        count(recipe_ingredient_id) as ingredient_count,
        count(distinct ingredient_id) as distinct_ingredients,
        sum(quantity) as total_quantity_units
    from recipe_ingredients
    group by 1

),

percentiles as (

    select
        recipe_id,
        ingredient_count,
        distinct_ingredients,
        total_quantity_units,
        ntile(5) over (order by ingredient_count asc) as ingredient_count_score,
        ntile(5) over (order by total_quantity_units asc) as quantity_complexity_score
    from recipe_stats

),

final as (

    select
        recipe_id,
        ingredient_count,
        distinct_ingredients,
        total_quantity_units,
        ingredient_count_score,
        quantity_complexity_score,
        round(cast((ingredient_count_score + quantity_complexity_score) / 2.0 as {{ dbt.type_float() }}), 1) as complexity_score,
        case
            when (ingredient_count_score + quantity_complexity_score) / 2.0 >= 4 then 'high'
            when (ingredient_count_score + quantity_complexity_score) / 2.0 >= 2.5 then 'medium'
            else 'low'
        end as complexity_tier
    from percentiles

)

select * from final
