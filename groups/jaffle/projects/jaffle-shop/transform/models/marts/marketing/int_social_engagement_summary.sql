with

social_posts as (

    select * from {{ ref('stg_social_media_posts') }}

),

-- Calculate engagement metrics per post
post_engagement as (

    select
        post_id,
        campaign_id,
        platform,
        post_type,
        posted_at,
        impressions,
        reach,
        likes,
        shares,
        comment_count,
        click_count,
        -- Total engagements = likes + shares + comments + clicks
        (coalesce(likes, 0) + coalesce(shares, 0) + coalesce(comment_count, 0) + coalesce(click_count, 0)) as total_engagements,
        -- Engagement rate = total engagements / impressions
        case
            when impressions > 0
            then (coalesce(likes, 0) + coalesce(shares, 0) + coalesce(comment_count, 0) + coalesce(click_count, 0)) * 1.0 / impressions
            else 0
        end as engagement_rate,
        -- Click-through rate
        case
            when impressions > 0
            then coalesce(click_count, 0) * 1.0 / impressions
            else 0
        end as click_through_rate

    from social_posts

),

-- Aggregate by platform
platform_summary as (

    select
        platform,
        count(post_id) as total_posts,
        sum(impressions) as total_impressions,
        sum(reach) as total_reach,
        sum(likes) as total_likes,
        sum(shares) as total_shares,
        sum(comment_count) as total_comments,
        sum(click_count) as total_clicks,
        sum(total_engagements) as total_engagements,
        avg(engagement_rate) as avg_engagement_rate,
        avg(click_through_rate) as avg_click_through_rate,
        min(posted_at) as first_post_date,
        max(posted_at) as last_post_date

    from post_engagement
    group by 1

)

select * from platform_summary
