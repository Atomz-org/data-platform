with

product_reviews as (

    select * from {{ ref('stg_product_reviews') }}

),

review_summary as (

    select
        product_id,
        count(*) as total_review_count,
        avg(rating) as avg_rating,
        min(rating) as min_rating,
        max(rating) as max_rating,
        sum(case when rating >= 4 then 1 else 0 end) as positive_review_count,
        sum(case when rating = 3 then 1 else 0 end) as neutral_review_count,
        sum(case when rating <= 2 then 1 else 0 end) as negative_review_count,
        sum(case when rating >= 4 then 1 else 0 end) * 1.0
            / nullif(count(*), 0) as positive_review_pct,
        sum(case when rating <= 2 then 1 else 0 end) * 1.0
            / nullif(count(*), 0) as negative_review_pct,
        min(reviewed_date) as first_review_date,
        max(reviewed_date) as last_review_date

    from product_reviews
    group by product_id

)

select * from review_summary
