with

reviews as (

    select * from {{ ref('stg_product_reviews') }}

),

monthly_reviews as (

    select
        product_id,
        {{ dbt.date_trunc('month', 'reviewed_date') }} as review_month,
        count(review_id) as review_count,
        avg(rating) as avg_rating,
        min(rating) as min_rating,
        max(rating) as max_rating,
        count(case when rating >= 4 then 1 end) as positive_reviews,
        count(case when rating <= 2 then 1 end) as negative_reviews
    from reviews
    group by 1, 2

),

final as (

    select
        product_id,
        review_month,
        review_count,
        avg_rating,
        min_rating,
        max_rating,
        positive_reviews,
        negative_reviews,
        avg(avg_rating) over (
            partition by product_id
            order by review_month
            rows between 2 preceding and current row
        ) as rolling_3m_avg_rating,
        case
            when avg_rating >= 4.0 then 'excellent'
            when avg_rating >= 3.0 then 'good'
            when avg_rating >= 2.0 then 'fair'
            else 'poor'
        end as rating_tier
    from monthly_reviews

)

select * from final
