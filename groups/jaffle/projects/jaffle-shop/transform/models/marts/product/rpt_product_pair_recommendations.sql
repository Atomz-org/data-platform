with

product_affinity as (

    select * from {{ ref('int_product_affinity') }}

),

products as (

    select * from {{ ref('stg_products') }}

),

enriched_pairs as (

    select
        pa.product_id_a,
        p_a.product_name as product_name_a,
        p_a.product_type as product_type_a,
        pa.product_id_b,
        p_b.product_name as product_name_b,
        p_b.product_type as product_type_b,
        pa.co_occurrence_count,
        pa.product_a_total_orders,
        pa.product_b_total_orders,
        pa.support_a,
        pa.support_b,
        pa.affinity_rank,
        -- Lift: how much more likely to co-occur than random chance
        case
            when pa.product_a_total_orders > 0 and pa.product_b_total_orders > 0
            then pa.co_occurrence_count * 1.0
                 / (pa.product_a_total_orders * pa.product_b_total_orders)
                 * (pa.product_a_total_orders + pa.product_b_total_orders)
            else null
        end as association_lift,
        -- Recommendation strength
        case
            when pa.affinity_rank = 1 and pa.support_a >= 0.3 then 'strong'
            when pa.affinity_rank <= 3 and pa.support_a >= 0.15 then 'moderate'
            when pa.affinity_rank <= 5 then 'weak'
            else 'insufficient_data'
        end as recommendation_strength,
        -- Cross-sell indicator: different product types are more valuable
        case
            when p_a.product_type != p_b.product_type then true
            else false
        end as is_cross_category_pair

    from product_affinity as pa
    inner join products as p_a
        on pa.product_id_a = p_a.product_id
    inner join products as p_b
        on pa.product_id_b = p_b.product_id
    where pa.affinity_rank <= 5

)

select * from enriched_pairs
