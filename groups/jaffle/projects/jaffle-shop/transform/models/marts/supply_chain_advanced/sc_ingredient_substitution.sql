with

ingredients as (

    select
        ingredient_id,
        ingredient_name,
        ingredient_category,
        default_unit,
        is_perishable,
        is_allergen
    from {{ ref('stg_ingredients') }}

),

recipe_usage as (

    select
        ingredient_id,
        count(distinct recipe_id) as recipe_count,
        avg(quantity) as avg_quantity_per_recipe
    from {{ ref('stg_recipe_ingredients') }}
    group by 1

),

same_category as (

    select
        a.ingredient_id as original_id,
        a.ingredient_name as original_name,
        a.ingredient_category,
        b.ingredient_id as substitute_id,
        b.ingredient_name as substitute_name,
        b.is_allergen as substitute_is_allergen,
        case
            when a.default_unit = b.default_unit then true
            else false
        end as same_unit,
        case
            when a.is_perishable = b.is_perishable then 1 else 0
        end as perishability_match
    from ingredients as a
    inner join ingredients as b
        on a.ingredient_category = b.ingredient_category
        and a.ingredient_id != b.ingredient_id

),

final as (

    select
        sc.original_id,
        sc.original_name,
        sc.ingredient_category,
        sc.substitute_id,
        sc.substitute_name,
        sc.same_unit,
        sc.perishability_match,
        sc.substitute_is_allergen,
        coalesce(ru.recipe_count, 0) as substitute_recipe_usage,
        case
            when sc.same_unit and sc.perishability_match = 1 then 'high_compatibility'
            when sc.same_unit then 'moderate_compatibility'
            else 'low_compatibility'
        end as substitution_fit
    from same_category as sc
    left join recipe_usage as ru on sc.substitute_id = ru.ingredient_id

)

select * from final
