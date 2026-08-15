with

product_review_summary as (

    select * from {{ ref('int_product_review_summary') }}

),

products as (

    select * from {{ ref('stg_products') }}

),

product_reviews as (

    select * from {{ ref('stg_product_reviews') }}

),

-- Monthly review trend
monthly_reviews as (

    select
        product_id,
        {{ dbt.date_trunc('month', 'reviewed_date') }} as review_month,
        count(*) as monthly_review_count,
        avg(rating) as monthly_avg_rating

    from product_reviews
    group by product_id, {{ dbt.date_trunc('month', 'reviewed_date') }}

),

-- Get latest month rating and trend
latest_trend as (

    select
        product_id,
        review_month,
        monthly_review_count,
        monthly_avg_rating,
        lag(monthly_avg_rating) over (
            partition by product_id order by review_month
        ) as prev_month_avg_rating,
        row_number() over (
            partition by product_id order by review_month desc
        ) as recency_rank

    from monthly_reviews

),

final as (

    select
        prs.product_id,
        p.product_name,
        p.product_type,
        prs.total_review_count,
        prs.avg_rating,
        prs.min_rating,
        prs.max_rating,
        prs.positive_review_count,
        prs.neutral_review_count,
        prs.negative_review_count,
        prs.positive_review_pct,
        prs.negative_review_pct,
        prs.first_review_date,
        prs.last_review_date,
        lt.monthly_avg_rating as latest_month_avg_rating,
        lt.monthly_review_count as latest_month_review_count,
        lt.prev_month_avg_rating,
        lt.monthly_avg_rating - coalesce(lt.prev_month_avg_rating, lt.monthly_avg_rating) as rating_trend,
        -- Sentiment classification
        case
            when prs.avg_rating >= 4.0 then 'positive'
            when prs.avg_rating >= 3.0 then 'neutral'
            else 'negative'
        end as overall_sentiment,
        -- Rating trend direction
        case
            when lt.monthly_avg_rating > coalesce(lt.prev_month_avg_rating, lt.monthly_avg_rating) + 0.2
            then 'improving'
            when lt.monthly_avg_rating < coalesce(lt.prev_month_avg_rating, lt.monthly_avg_rating) - 0.2
            then 'declining'
            else 'stable'
        end as rating_trend_direction

    from product_review_summary as prs
    inner join products as p
        on prs.product_id = p.product_id
    left join latest_trend as lt
        on prs.product_id = lt.product_id
        and lt.recency_rank = 1

)

select * from final
