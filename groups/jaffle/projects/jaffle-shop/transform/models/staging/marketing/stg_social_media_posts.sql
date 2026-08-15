with

source as (

    select * from {{ source('marketing', 'raw_social_media_posts') }}

),

renamed as (

    select

        ----------  ids
        cast(id as varchar) as post_id,
        cast(campaign_id as varchar) as campaign_id,

        ---------- text
        platform,
        post_type,
        content as post_content,
        url as post_url,

        ---------- numerics
        impressions,
        reach,
        likes,
        shares,
        comments as comment_count,
        clicks as click_count,

        ---------- timestamps
        {{ dbt.date_trunc('day', 'posted_at') }} as posted_at

    from source

)

select * from renamed
