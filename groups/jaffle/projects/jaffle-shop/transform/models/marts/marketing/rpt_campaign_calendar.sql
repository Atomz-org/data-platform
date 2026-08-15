with

campaigns as (

    select * from {{ ref('dim_campaigns') }}

),

campaign_effectiveness as (

    select * from {{ ref('rpt_campaign_effectiveness') }}

),

-- Identify overlapping campaigns
campaign_overlaps as (

    select
        a.campaign_id as campaign_id_a,
        a.campaign_name as campaign_name_a,
        b.campaign_id as campaign_id_b,
        b.campaign_name as campaign_name_b,
        -- Overlap period
        {{ sf_greatest(["a.campaign_start_date", "b.campaign_start_date"]) }} as overlap_start,
        {{ sf_least(["(coalesce(a.campaign_end_date, current_date))", "(coalesce(b.campaign_end_date, current_date))"]) }} as overlap_end

    from campaigns as a

    inner join campaigns as b
        on a.campaign_id < b.campaign_id
        and a.campaign_start_date <= coalesce(b.campaign_end_date, current_date)
        and b.campaign_start_date <= coalesce(a.campaign_end_date, current_date)

),

-- Count concurrent campaigns per campaign
concurrent_counts as (

    select
        campaign_id_a as campaign_id,
        count(distinct campaign_id_b) as concurrent_campaigns

    from campaign_overlaps
    group by 1

    union all

    select
        campaign_id_b as campaign_id,
        count(distinct campaign_id_a) as concurrent_campaigns

    from campaign_overlaps
    group by 1

),

concurrent_summary as (

    select
        campaign_id,
        sum(concurrent_campaigns) as total_concurrent_campaigns

    from concurrent_counts
    group by 1

),

-- Final campaign timeline view
final as (

    select
        campaigns.campaign_id,
        campaigns.campaign_name,
        campaigns.campaign_channel,
        campaigns.campaign_status,
        campaigns.campaign_start_date,
        campaigns.campaign_end_date,
        campaigns.campaign_duration_days,
        campaigns.is_currently_active,
        campaign_effectiveness.total_spend,
        campaign_effectiveness.attributed_revenue,
        campaign_effectiveness.roi_ratio,
        campaign_effectiveness.effectiveness_tier,
        coalesce(concurrent_summary.total_concurrent_campaigns, 0) as concurrent_campaign_count,
        -- Campaign phase
        case
            when campaigns.campaign_start_date > current_date then 'upcoming'
            when campaigns.is_currently_active then 'active'
            when campaigns.campaign_end_date < current_date then 'completed'
            else 'unknown'
        end as campaign_phase

    from campaigns

    left join campaign_effectiveness
        on campaigns.campaign_id = campaign_effectiveness.campaign_id

    left join concurrent_summary
        on campaigns.campaign_id = concurrent_summary.campaign_id

)

select * from final
order by campaign_start_date
