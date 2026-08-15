with

ingredient_usage_daily as (

    select * from {{ ref('int_ingredient_usage_daily') }}

),

ingredients as (

    select * from {{ ref('stg_ingredients') }}

),

final as (

    select
        iud.order_date,
        iud.ingredient_id,
        i.ingredient_name,
        i.ingredient_category,
        i.is_perishable,
        i.is_allergen,
        iud.quantity_unit,
        iud.total_quantity_used,
        iud.order_item_count,
        avg(iud.total_quantity_used) over (
            partition by iud.ingredient_id
            order by iud.order_date
            rows between 6 preceding and current row
        ) as rolling_7d_avg_usage

    from ingredient_usage_daily as iud
    inner join ingredients as i
        on iud.ingredient_id = i.ingredient_id

)

select * from final
