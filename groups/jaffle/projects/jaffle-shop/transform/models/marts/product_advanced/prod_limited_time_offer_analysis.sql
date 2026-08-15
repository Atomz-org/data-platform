with

seasonal_items as (

    select
        menu_item_id,
        season_name,
        promotion_name,
        promotion_start_date,
        promotion_end_date,
        is_active_promotion
    from {{ ref('stg_seasonal_menus') }}

),

sales as (

    select
        product_id,
        sale_date,
        units_sold,
        daily_revenue
    from {{ ref('fct_product_sales') }}

),

lto_performance as (

    select
        si.menu_item_id,
        si.season_name,
        si.promotion_name,
        si.promotion_start_date,
        si.promotion_end_date,
        sum(s.units_sold) as total_qty_during_promo,
        sum(s.daily_revenue) as daily_revenue_during_promo,
        count(distinct s.sale_date) as active_sale_days,
        {{ dbt.datediff('si.promotion_start_date', 'si.promotion_end_date', 'day') }} as promo_duration_days
    from seasonal_items as si
    inner join sales as s
        on si.menu_item_id = s.product_id
        and s.sale_date between si.promotion_start_date and si.promotion_end_date
    group by 1, 2, 3, 4, 5

),

permanent_items_avg as (

    select
        avg(units_sold) as avg_daily_qty_permanent
    from sales as s
    where not exists (
        select 1 from seasonal_items si
        where si.menu_item_id = s.product_id
    )

),

final as (

    select
        lp.menu_item_id,
        lp.season_name,
        lp.promotion_name,
        lp.promotion_start_date,
        lp.promotion_end_date,
        lp.promo_duration_days,
        lp.total_qty_during_promo,
        lp.daily_revenue_during_promo,
        lp.active_sale_days,
        case
            when lp.active_sale_days > 0
            then cast(lp.total_qty_during_promo as {{ dbt.type_float() }}) / lp.active_sale_days
            else 0
        end as avg_daily_qty,
        case
            when pa.avg_daily_qty_permanent > 0
            then (cast(lp.total_qty_during_promo as {{ dbt.type_float() }}) / nullif(lp.active_sale_days, 0))
                / pa.avg_daily_qty_permanent
            else null
        end as performance_vs_permanent_ratio
    from lto_performance as lp
    cross join permanent_items_avg as pa

)

select * from final
