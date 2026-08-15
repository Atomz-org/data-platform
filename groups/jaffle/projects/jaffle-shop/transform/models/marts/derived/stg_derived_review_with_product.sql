with

reviews as (
    select * from {{ ref('stg_product_reviews') }}
),

products as (
    select product_id, product_name, product_type from {{ ref('stg_products') }}
),

final as (
    select
        r.review_id,
        r.product_id,
        p.product_name,
        p.product_type,
        r.customer_id,
        r.rating,
        r.reviewed_date,
        r.review_title,
        r.review_body
    from reviews as r
    left join products as p on r.product_id = p.product_id
)

select * from final
