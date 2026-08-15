with

popularity as (

    select * from {{ ref('int_menu_item_popularity_rank') }}

),

margins as (

    select
        menu_item_id,
        menu_item_name,
        menu_item_price,
        category_name,
        gross_margin,
        gross_margin_pct
    from {{ ref('int_menu_item_margin') }}

),

reviews as (

    select * from {{ ref('int_product_review_summary') }}

),

combined as (

    select
        p.product_id,
        p.product_name,
        p.product_type,
        p.category_name,
        p.total_units_sold,
        p.total_revenue,
        p.overall_volume_rank,
        p.overall_revenue_rank,
        p.volume_rank_in_category,
        p.revenue_rank_in_category,
        coalesce(m.gross_margin, 0) as gross_margin,
        coalesce(m.gross_margin_pct, 0) as gross_margin_pct,
        coalesce(r.avg_rating, 0) as avg_rating,
        coalesce(r.total_review_count, 0) as total_reviews,
        coalesce(r.positive_review_pct, 0) as positive_review_pct

    from popularity as p

    left join margins as m
        on p.product_id = m.menu_item_id

    left join reviews as r
        on p.product_id = r.product_id

),

scored as (

    select
        *,
        -- Composite score: weighted blend of revenue contribution, margin, popularity, and reviews
        -- Revenue contribution (weight: 30%)
        round((total_revenue * 1.0 / nullif(sum(total_revenue) over (), 0)) * 30
            -- Margin (weight: 30%)
            + ({{ sf_least(["gross_margin_pct", "100"]) }} / 100.0) * 30
            -- Popularity / volume (weight: 20%)
            + (total_units_sold * 1.0 / nullif(sum(total_units_sold) over (), 0)) * 20
            -- Review rating (weight: 20%)
            + ({{ sf_least(["avg_rating", "5"]) }} / 5.0) * 20, 2) as composite_score

    from combined

),

ranked as (

    select
        *,
        rank() over (order by composite_score desc) as overall_composite_rank,
        rank() over (
            partition by category_name
            order by composite_score desc
        ) as category_composite_rank

    from scored

)

select * from ranked
