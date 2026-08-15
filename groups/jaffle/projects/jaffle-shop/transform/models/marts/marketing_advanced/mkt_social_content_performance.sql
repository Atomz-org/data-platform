with

posts as (

    select
        post_id,
        campaign_id,
        platform,
        post_type,
        posted_at,
        likes,
        shares,
        comment_count,
        impressions,
        likes + shares + comment_count as total_engagement
    from {{ ref('stg_social_media_posts') }}

),

by_type as (

    select
        platform,
        post_type,
        count(*) as post_count,
        sum(total_engagement) as total_engagement,
        avg(total_engagement) as avg_engagement_per_post,
        sum(impressions) as total_impressions,
        case
            when sum(impressions) > 0
            then cast(sum(total_engagement) as {{ dbt.type_float() }}) / sum(impressions) * 100
            else 0
        end as engagement_rate_pct,
        avg(likes) as avg_likes,
        avg(shares) as avg_shares,
        avg(comment_count) as avg_comment_count
    from posts
    group by 1, 2

),

final as (

    select
        platform,
        post_type,
        post_count,
        total_engagement,
        avg_engagement_per_post,
        total_impressions,
        engagement_rate_pct,
        avg_likes,
        avg_shares,
        avg_comment_count,
        rank() over (partition by platform order by avg_engagement_per_post desc) as engagement_rank
    from by_type

)

select * from final
