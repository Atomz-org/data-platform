with

affinity as (
    select
        product_id_a,
        product_id_b,
        co_occurrence_count,
        support_a,
        support_b,
        affinity_rank
    from {{ ref('int_product_affinity') }}
),

products as (
    select product_id, product_name
    from {{ ref('stg_products') }}
),

margins as (
    select menu_item_id as product_id, gross_margin
    from {{ ref('int_menu_item_margin') }}
),

final as (
    select
        a.product_id_a,
        pa.product_name as product_a_name,
        a.product_id_b,
        pb.product_name as product_b_name,
        a.co_occurrence_count,
        a.support_a as affinity_score,
        coalesce(ma.gross_margin, 0) + coalesce(mb.gross_margin, 0) as combined_margin,
        case
            when a.support_a > 0.5 and a.co_occurrence_count > 50 then 'strong_bundle'
            when a.support_a > 0.3 then 'moderate_bundle'
            else 'weak_bundle'
        end as bundle_strength,
        rank() over (
            partition by a.product_id_a
            order by a.co_occurrence_count desc
        ) as pair_rank
    from affinity as a
    inner join products as pa on a.product_id_a = pa.product_id
    inner join products as pb on a.product_id_b = pb.product_id
    left join margins as ma on a.product_id_a = ma.product_id
    left join margins as mb on a.product_id_b = mb.product_id
)

select * from final
where pair_rank <= 5
