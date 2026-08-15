with

pricing_history as (

    select * from {{ ref('stg_pricing_history') }}

),

products as (

    select * from {{ ref('stg_products') }}

),

final as (

    select
        ph.pricing_history_id,
        ph.product_id,
        p.product_name,
        p.product_type,
        ph.old_price,
        ph.new_price,
        ph.new_price - ph.old_price as price_change_amount,
        case
            when ph.old_price > 0
            then (ph.new_price - ph.old_price) / ph.old_price * 100
            else null
        end as price_change_pct,
        case
            when ph.new_price > ph.old_price then 'increase'
            when ph.new_price < ph.old_price then 'decrease'
            else 'no_change'
        end as price_change_direction,
        ph.change_reason,
        ph.price_changed_date,
        lag(ph.price_changed_date) over (
            partition by ph.product_id
            order by ph.price_changed_date
        ) as previous_change_date

    from pricing_history as ph
    inner join products as p
        on ph.product_id = p.product_id

)

select * from final
