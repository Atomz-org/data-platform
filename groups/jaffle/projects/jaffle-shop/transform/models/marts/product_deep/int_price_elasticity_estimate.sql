with

pricing_history as (

    select * from {{ ref('stg_pricing_history') }}

),

product_sales as (

    select
        product_id,
        sale_date,
        units_sold,
        daily_revenue as total_revenue
    from {{ ref('int_product_sales_daily') }}

),

price_changes as (

    select
        product_id,
        old_price,
        new_price,
        price_changed_date,
        case
            when old_price > 0
                then (new_price - old_price) / old_price
            else null
        end as price_change_pct
    from pricing_history
    where old_price > 0

),

pre_post_sales as (

    select
        pc.product_id,
        pc.price_changed_date,
        pc.old_price,
        pc.new_price,
        pc.price_change_pct,
        avg(case
            when ps.sale_date between {{ dbt.dateadd('day', -14, 'pc.price_changed_date') }}
                and {{ dbt.dateadd('day', -1, 'pc.price_changed_date') }}
            then ps.units_sold
            else null
        end) as avg_daily_sales_before,
        avg(case
            when ps.sale_date between pc.price_changed_date
                and {{ dbt.dateadd('day', 13, 'pc.price_changed_date') }}
            then ps.units_sold
            else null
        end) as avg_daily_sales_after
    from price_changes as pc
    left join product_sales as ps
        on pc.product_id = ps.product_id
        and ps.sale_date between {{ dbt.dateadd('day', -14, 'pc.price_changed_date') }}
            and {{ dbt.dateadd('day', 13, 'pc.price_changed_date') }}
    group by 1, 2, 3, 4, 5

),

final as (

    select
        product_id,
        price_changed_date,
        old_price,
        new_price,
        price_change_pct,
        avg_daily_sales_before,
        avg_daily_sales_after,
        case
            when avg_daily_sales_before > 0
                then (avg_daily_sales_after - avg_daily_sales_before) / avg_daily_sales_before
            else null
        end as volume_change_pct,
        case
            when price_change_pct != 0 and avg_daily_sales_before > 0
                then round(cast(
                    ((avg_daily_sales_after - avg_daily_sales_before) / avg_daily_sales_before)
                    / price_change_pct
                as {{ dbt.type_float() }}), 2)
            else null
        end as estimated_elasticity
    from pre_post_sales

)

select * from final
