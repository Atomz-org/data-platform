with

social_summary as (

    select
        platform,
        {{ dbt.date_trunc('month', 'posted_at') }} as summary_month,
        sum(coalesce(likes, 0) + coalesce(shares, 0) + coalesce(comment_count, 0) + coalesce(click_count, 0)) as total_engagement,
        sum(impressions) as total_impressions,
        count(post_id) as post_count
    from {{ ref('stg_social_media_posts') }}
    group by 1, 2

),

with_growth as (

    select
        platform,
        summary_month,
        total_engagement,
        total_impressions,
        post_count,
        lag(total_engagement) over (partition by platform order by summary_month) as prev_month_engagement,
        lag(total_impressions) over (partition by platform order by summary_month) as prev_month_impressions
    from social_summary

),

final as (

    select
        platform,
        summary_month,
        total_engagement,
        total_impressions,
        post_count,
        case
            when prev_month_engagement > 0
            then (total_engagement - prev_month_engagement) / cast(prev_month_engagement as {{ dbt.type_float() }}) * 100
            else null
        end as engagement_growth_pct,
        case
            when prev_month_impressions > 0
            then (total_impressions - prev_month_impressions) / cast(prev_month_impressions as {{ dbt.type_float() }}) * 100
            else null
        end as impressions_growth_pct,
        case
            when total_impressions > 0
            then cast(total_engagement as {{ dbt.type_float() }}) / total_impressions * 100
            else 0
        end as engagement_rate_pct
    from with_growth

)

select * from final
