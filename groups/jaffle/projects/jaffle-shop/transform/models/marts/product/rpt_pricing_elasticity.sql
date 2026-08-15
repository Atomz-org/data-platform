with

pricing_changes as (

    select * from {{ ref('fct_pricing_changes') }}

),

product_sales_daily as (

    select * from {{ ref('int_product_sales_daily') }}

),

pre_change_sales as (

    select
        pc.pricing_history_id,
        pc.product_id,
        avg(psd.units_sold) as avg_daily_units_before

    from pricing_changes as pc
    inner join product_sales_daily as psd
        on pc.product_id = psd.product_id
        and psd.sale_date >= {{ dbt.dateadd('day', -30, 'pc.price_changed_date') }}
        and psd.sale_date < pc.price_changed_date
    group by pc.pricing_history_id, pc.product_id

),

post_change_sales as (

    select
        pc.pricing_history_id,
        pc.product_id,
        avg(psd.units_sold) as avg_daily_units_after

    from pricing_changes as pc
    inner join product_sales_daily as psd
        on pc.product_id = psd.product_id
        and psd.sale_date >= pc.price_changed_date
        and psd.sale_date < {{ dbt.dateadd('day', 30, 'pc.price_changed_date') }}
    group by pc.pricing_history_id, pc.product_id

),

final as (

    select
        pc.pricing_history_id,
        pc.product_id,
        pc.product_name,
        pc.product_type,
        pc.old_price,
        pc.new_price,
        pc.price_change_amount,
        pc.price_change_pct,
        pc.price_change_direction,
        pc.change_reason,
        pc.price_changed_date,
        pre.avg_daily_units_before,
        post.avg_daily_units_after,
        case
            when coalesce(pre.avg_daily_units_before, 0) > 0
            then (coalesce(post.avg_daily_units_after, 0) - pre.avg_daily_units_before)
                 / pre.avg_daily_units_before * 100
            else null
        end as volume_change_pct,
        case
            when coalesce(pc.price_change_pct, 0) != 0
                and coalesce(pre.avg_daily_units_before, 0) > 0
            then ((coalesce(post.avg_daily_units_after, 0) - pre.avg_daily_units_before)
                 / pre.avg_daily_units_before * 100)
                 / pc.price_change_pct
            else null
        end as price_elasticity

    from pricing_changes as pc
    left join pre_change_sales as pre
        on pc.pricing_history_id = pre.pricing_history_id
    left join post_change_sales as post
        on pc.pricing_history_id = post.pricing_history_id

)

select * from final
