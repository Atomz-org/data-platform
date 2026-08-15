-- adv_latest_price_per_product.sql
-- Technique: ROW_NUMBER() window function (cross-database compatible)
-- Gets the most recent price for each product using ROW_NUMBER() to keep only
-- the first row per group after ordering.

with pricing_history as (

    select * from {{ ref('stg_pricing_history') }}

),

products as (

    select * from {{ ref('stg_products') }}

),

-- ROW_NUMBER: for each product_id, keep only the row with the latest price_changed_date
ranked_prices as (

    select
        ph.product_id,
        p.product_name,
        p.product_type,
        ph.new_price as current_price,
        ph.old_price as previous_price,
        ph.change_reason as last_change_reason,
        ph.price_changed_date as last_price_change_date,
        -- Calculate price change metrics
        ph.new_price - ph.old_price as price_change_amount,
        case
            when ph.old_price > 0
            then round(ph.new_price - ph.old_price / ph.old_price * 100, 1)
            else null
        end as price_change_pct,
        row_number() over (partition by ph.product_id order by ph.price_changed_date desc) as _rn
    from pricing_history as ph
    inner join products as p
        on ph.product_id = p.product_id

),

latest_price as (

    select
        product_id,
        product_name,
        product_type,
        current_price,
        previous_price,
        last_change_reason,
        last_price_change_date,
        price_change_amount,
        price_change_pct
    from ranked_prices
    where _rn = 1

)

select * from latest_price
order by product_id
