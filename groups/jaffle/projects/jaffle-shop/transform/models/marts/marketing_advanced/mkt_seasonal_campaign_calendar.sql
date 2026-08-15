with

campaigns as (

    select
        campaign_id,
        campaign_name,
        campaign_channel,
        campaign_start_date,
        campaign_end_date,
        extract(month from campaign_start_date) as start_month
    from {{ ref('dim_campaigns') }}

),

roi as (

    select
        campaign_id,
        total_spend,
        attributed_revenue
    from {{ ref('int_campaign_roi') }}

),

monthly_pattern as (

    select
        c.start_month,
        c.campaign_channel,
        count(*) as campaigns_run,
        avg(r.total_spend) as avg_roi,
        sum(r.attributed_revenue) as total_revenue,
        sum(r.total_spend) as total_spend,
        avg(r.attributed_revenue) as avg_revenue_per_campaign
    from campaigns as c
    left join roi as r on c.campaign_id = r.campaign_id
    group by 1, 2

),

final as (

    select
        start_month,
        campaign_channel,
        campaigns_run,
        avg_roi,
        total_revenue,
        total_spend,
        avg_revenue_per_campaign,
        case
            when avg_roi > 200 then 'high_performing_season'
            when avg_roi > 100 then 'good_season'
            when avg_roi > 0 then 'break_even_season'
            else 'underperforming_season'
        end as season_rating
    from monthly_pattern

)

select * from final
