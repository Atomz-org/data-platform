with

ingredient_cost_trend as (

    select * from {{ ref('int_ingredient_cost_trend') }}

),

ingredients as (

    select * from {{ ref('stg_ingredients') }}

),

final as (

    select
        ict.ingredient_id,
        i.ingredient_name,
        i.ingredient_category,
        i.is_perishable,
        ict.price_month,
        ict.avg_unit_cost,
        ict.min_unit_cost,
        ict.max_unit_cost,
        ict.prev_month_avg_cost,
        ict.mom_cost_change_pct,
        ict.price_record_count,
        case
            when ict.mom_cost_change_pct > 10 then 'significant_increase'
            when ict.mom_cost_change_pct > 5 then 'moderate_increase'
            when ict.mom_cost_change_pct < -10 then 'significant_decrease'
            when ict.mom_cost_change_pct < -5 then 'moderate_decrease'
            else 'stable'
        end as price_trend_status,
        case
            when abs(coalesce(ict.mom_cost_change_pct, 0)) > 10 then true
            else false
        end as requires_attention

    from ingredient_cost_trend as ict
    inner join ingredients as i
        on ict.ingredient_id = i.ingredient_id

)

select * from final
