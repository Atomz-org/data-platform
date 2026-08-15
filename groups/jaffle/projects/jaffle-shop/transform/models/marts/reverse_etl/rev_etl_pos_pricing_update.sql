with

pricing_changes as (

    select * from {{ ref('fct_pricing_changes') }}

),

latest_price as (

    select
        product_id,
        new_price,
        old_price,
        price_changed_date,
        row_number() over (partition by product_id order by price_changed_date desc) as rn

    from pricing_changes

)

select
    product_id,
    new_price as current_price,
    old_price as previous_price,
    price_changed_date as price_price_changed_date,
    round(new_price - old_price, 2) as price_change,
    round(new_price - old_price * 100.0 / nullif(old_price, 0), 2) as price_change_pct,
    current_timestamp as exported_at

from latest_price
where rn = 1
