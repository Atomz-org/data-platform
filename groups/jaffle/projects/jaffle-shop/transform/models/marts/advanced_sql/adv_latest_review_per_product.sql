-- adv_latest_review_per_product.sql
-- Technique: ROW_NUMBER() window function (cross-database compatible)
-- Gets the most recent review for each product using ROW_NUMBER().

with product_reviews as (

    select * from {{ ref('stg_product_reviews') }}

),

products as (

    select * from {{ ref('stg_products') }}

),

customers as (

    select * from {{ ref('stg_customers') }}

),

-- ROW_NUMBER keeps the first row per product_id after ordering by reviewed_date desc
ranked_reviews as (

    select
        pr.product_id,
        p.product_name,
        p.product_type,
        pr.review_id,
        pr.customer_id,
        c.customer_name as reviewer_name,
        pr.rating,
        pr.review_title,
        pr.review_body,
        pr.reviewed_date as latest_review_date,
        row_number() over (partition by pr.product_id order by pr.reviewed_date desc) as _rn
    from product_reviews as pr
    inner join products as p
        on pr.product_id = p.product_id
    inner join customers as c
        on pr.customer_id = c.customer_id

),

latest_review as (

    select
        product_id,
        product_name,
        product_type,
        review_id,
        customer_id,
        reviewer_name,
        rating,
        review_title,
        review_body,
        latest_review_date
    from ranked_reviews
    where _rn = 1

),

-- Enrich with overall product review stats
review_stats as (

    select
        product_id,
        count(review_id) as total_reviews,
        round(avg(rating), 2) as avg_rating,
        min(rating) as min_rating,
        max(rating) as max_rating
    from product_reviews
    group by 1

)

select
    lr.product_id,
    lr.product_name,
    lr.product_type,
    lr.review_id,
    lr.reviewer_name,
    lr.rating as latest_rating,
    lr.review_title as latest_review_title,
    lr.review_body as latest_review_body,
    lr.latest_review_date,
    rs.total_reviews,
    rs.avg_rating,
    -- Flag if latest review deviates significantly from average
    case
        when lr.rating >= rs.avg_rating + 1 then 'above_average'
        when lr.rating <= rs.avg_rating - 1 then 'below_average'
        else 'typical'
    end as latest_vs_average
from latest_review as lr
left join review_stats as rs
    on lr.product_id = rs.product_id
order by lr.product_id
