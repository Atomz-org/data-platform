with

popularity as (
    select
        product_id,
        overall_volume_rank as popularity_rank,
        total_units_sold
    from {{ ref('int_menu_item_popularity_rank') }}
),

margins as (
    select
        menu_item_id as product_id,
        gross_margin,
        gross_margin_pct
    from {{ ref('int_menu_item_margin') }}
),

items as (
    select
        product_id,
        menu_item_name as item_name,
        category_name
    from {{ ref('dim_menu_items') }}
),

percentiles as (
    select
        avg(total_units_sold) as median_popularity,
        avg(gross_margin_pct) as median_margin
    from popularity p
    inner join margins m on p.product_id = m.product_id
),

final as (
    select
        i.product_id,
        i.item_name,
        i.category_name,
        p.popularity_rank,
        p.total_units_sold,
        m.gross_margin,
        m.gross_margin_pct,
        case
            when p.total_units_sold >= pctl.median_popularity and m.gross_margin_pct >= pctl.median_margin then 'star'
            when p.total_units_sold >= pctl.median_popularity and m.gross_margin_pct < pctl.median_margin then 'plow_horse'
            when p.total_units_sold < pctl.median_popularity and m.gross_margin_pct >= pctl.median_margin then 'puzzle'
            else 'dog'
        end as matrix_quadrant,
        case
            when p.total_units_sold >= pctl.median_popularity and m.gross_margin_pct >= pctl.median_margin
            then 'maintain_and_promote'
            when p.total_units_sold >= pctl.median_popularity and m.gross_margin_pct < pctl.median_margin
            then 'increase_price_or_reduce_cost'
            when p.total_units_sold < pctl.median_popularity and m.gross_margin_pct >= pctl.median_margin
            then 'increase_visibility'
            else 'consider_removing'
        end as recommendation
    from items as i
    inner join popularity as p on i.product_id = p.product_id
    inner join margins as m on i.product_id = m.product_id
    cross join percentiles as pctl
)

select * from final
