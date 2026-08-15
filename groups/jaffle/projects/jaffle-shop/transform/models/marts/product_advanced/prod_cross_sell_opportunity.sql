with

affinity as (

    select
        product_id_a,
        product_id_b,
        co_occurrence_count,
        support_a
    from {{ ref('int_product_affinity') }}

),

products as (

    select product_id, product_name, product_type
    from {{ ref('stg_products') }}

),

-- Low frequency but high affinity = cross-sell opportunity
opportunities as (

    select
        a.product_id_a,
        pa.product_name as product_a_name,
        a.product_id_b,
        pb.product_name as product_b_name,
        a.co_occurrence_count,
        a.support_a,
        case
            when a.support_a > 0.5 and a.co_occurrence_count < 20 then 'high_potential'
            when a.support_a > 0.3 and a.co_occurrence_count < 50 then 'moderate_potential'
            else 'low_potential'
        end as opportunity_level
    from affinity as a
    inner join products as pa on a.product_id_a = pa.product_id
    inner join products as pb on a.product_id_b = pb.product_id
    where a.support_a > 0.2 and a.co_occurrence_count < 50

)

select * from opportunities
