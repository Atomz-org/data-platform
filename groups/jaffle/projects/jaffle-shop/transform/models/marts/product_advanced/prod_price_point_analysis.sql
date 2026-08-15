with

ps as (
    select * from {{ ref('fct_product_sales') }}
),

price_changes as (

    select
        product_id,
        old_price,
        new_price,
        price_changed_date,
        change_reason
    from {{ ref('fct_pricing_changes') }}

),

sales_around_change as (

    select
        pc.product_id,
        pc.price_changed_date,
        pc.old_price,
        pc.new_price,
        sum(case when ps.sale_date between {{ dbt.dateadd('day', '-30', 'pc.price_changed_date') }} and pc.price_changed_date
                 then ps.units_sold else 0 end) as pre_change_qty,
        sum(case when ps.sale_date between pc.price_changed_date and {{ dbt.dateadd('day', '30', 'pc.price_changed_date') }}
                 then ps.units_sold else 0 end) as post_change_qty
    from price_changes as pc
    left join ps
        on pc.product_id = ps.product_id
    group by 1, 2, 3, 4

),

final as (

    select
        product_id,
        price_changed_date,
        old_price,
        new_price,
        new_price - old_price as price_change,
        case when old_price > 0 then (new_price - old_price) / old_price * 100 else 0 end as price_change_pct,
        pre_change_qty,
        post_change_qty,
        post_change_qty - pre_change_qty as quantity_change,
        case
            when pre_change_qty > 0
            then (cast(post_change_qty - pre_change_qty as {{ dbt.type_float() }}) / pre_change_qty) * 100
            else null
        end as quantity_change_pct,
        -- Price elasticity approximation
        case
            when (new_price - old_price) / nullif(old_price, 0) != 0 and pre_change_qty > 0
            then ((cast(post_change_qty - pre_change_qty as {{ dbt.type_float() }}) / pre_change_qty))
                / ((new_price - old_price) / old_price)
            else null
        end as price_elasticity_estimate
    from sales_around_change

)

select * from final
