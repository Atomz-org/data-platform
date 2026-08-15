with

social_posts as (

    select * from {{ ref('stg_social_media_posts') }}

),

final as (

    select
        platform,
        post_type,
        {{ day_of_week_number('posted_at') }} as day_of_week,
        case {{ day_of_week_number('posted_at') }}
            when 0 then 'Sunday'
            when 1 then 'Monday'
            when 2 then 'Tuesday'
            when 3 then 'Wednesday'
            when 4 then 'Thursday'
            when 5 then 'Friday'
            when 6 then 'Saturday'
        end as day_name,
        count(post_id) as post_count,
        avg(impressions) as avg_impressions,
        avg(reach) as avg_reach,
        avg(likes) as avg_likes,
        avg(shares) as avg_shares,
        avg(click_count) as avg_clicks,
        sum(likes + shares + comment_count + click_count) as total_engagements,
        case
            when sum(impressions) > 0
                then round(cast(
                    sum(likes + shares + comment_count + click_count) * 100.0 / sum(impressions)
                as {{ dbt.type_float() }}), 2)
            else 0
        end as engagement_rate_pct
    from social_posts
    group by 1, 2, 3, 4

)

select * from final
