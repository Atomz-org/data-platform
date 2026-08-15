-- adv_products_never_wasted.sql
-- Technique: NOT EXISTS anti-join pattern
-- Finds products that have never appeared in a waste event. This is useful for
-- identifying products with perfect inventory management or those that sell
-- through completely before expiration. NOT EXISTS cleanly expresses "no matching
-- row" without the NULL-handling complexity of LEFT JOIN.

with products as (

    select * from {{ ref('stg_products') }}

),

waste_events as (

    select * from {{ ref('fct_waste_events') }}

),

-- NOT EXISTS: return products where no waste event row exists
products_without_waste as (

    select
        p.product_id,
        p.product_name,
        p.product_type,
        p.product_price

    from products as p

    where not exists (
        select 1
        from waste_events as w
        where w.product_id = p.product_id
    )

)

select
    product_id,
    product_name,
    product_type,
    product_price,
    -- Business insight: zero-waste products may indicate high demand,
    -- conservative ordering, or products with long shelf life
    case
        when product_type = 'jaffle' then 'zero_waste_food'
        when product_type = 'beverage' then 'zero_waste_beverage'
        else 'zero_waste_other'
    end as waste_category
from products_without_waste
order by product_type, product_name
