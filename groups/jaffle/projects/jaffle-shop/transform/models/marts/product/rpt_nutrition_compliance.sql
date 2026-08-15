with

menu_items as (

    select * from {{ ref('int_menu_item_enriched') }}

),

final as (

    select
        menu_item_id,
        menu_item_name,
        menu_item_size,
        category_name,
        product_type,
        is_available,
        calories,
        total_fat_g,
        sodium_mg,
        total_sugars_g,
        protein_g,
        caffeine_mg,

        -- calorie thresholds
        case when coalesce(calories, 0) > 600 then true else false end
            as exceeds_calorie_threshold,
        case when coalesce(calories, 0) > 800 then true else false end
            as exceeds_high_calorie_threshold,

        -- sodium threshold (2300mg daily recommended, flag items over 1000mg)
        case when coalesce(sodium_mg, 0) > 1000 then true else false end
            as exceeds_sodium_threshold,

        -- sugar threshold (flag items over 50g added sugar)
        case when coalesce(total_sugars_g, 0) > 50 then true else false end
            as exceeds_sugar_threshold,

        -- caffeine threshold (flag items over 400mg)
        case when coalesce(caffeine_mg, 0) > 400 then true else false end
            as exceeds_caffeine_threshold,

        -- overall compliance
        case
            when coalesce(calories, 0) > 800
                or coalesce(sodium_mg, 0) > 1000
                or coalesce(total_sugars_g, 0) > 50
                or coalesce(caffeine_mg, 0) > 400
            then 'non_compliant'
            when coalesce(calories, 0) > 600
            then 'warning'
            else 'compliant'
        end as compliance_status,

        -- flag count for prioritization
        (case when coalesce(calories, 0) > 600 then 1 else 0 end)
        + (case when coalesce(sodium_mg, 0) > 1000 then 1 else 0 end)
        + (case when coalesce(total_sugars_g, 0) > 50 then 1 else 0 end)
        + (case when coalesce(caffeine_mg, 0) > 400 then 1 else 0 end)
            as flag_count

    from menu_items

)

select * from final
