with

product_reviews as (
    select
        product_id,
        count(*) as review_count,
        round(avg(rating), 2) as avg_rating,
        count(case when rating >= 4 then 1 end) as positive_count
    from {{ ref('stg_product_reviews') }}
    group by 1
),

ranked as (
    select
        product_id,
        review_count,
        avg_rating,
        positive_count,
        round(positive_count * 100.0 / nullif(review_count, 0), 2) as positive_pct,
        rank() over (order by avg_rating desc, review_count desc) as rating_rank,
        ntile(5) over (order by avg_rating desc) as rating_quintile
    from product_reviews
    where review_count >= 3
)

select * from ranked
