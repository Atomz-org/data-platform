with

campaigns as (

    select
        campaign_id,
        campaign_name,
        campaign_channel,
        campaign_start_date,
        campaign_end_date
    from {{ ref('dim_campaigns') }}

),

roi as (

    select
        campaign_id,
        total_spend,
        attributed_revenue
    from {{ ref('int_campaign_roi') }}

),

-- Find overlapping campaigns
overlapping as (

    select
        a.campaign_id as campaign_a,
        b.campaign_id as campaign_b,
        a.campaign_name as campaign_a_name,
        b.campaign_name as campaign_b_name,
        {{ sf_greatest(["a.campaign_start_date", "b.campaign_start_date"]) }} as overlap_start,
        {{ sf_least(["a.campaign_end_date", "b.campaign_end_date"]) }} as overlap_end,
        {{ dbt.datediff('greatest(a.campaign_start_date, b.campaign_start_date)', 'least(a.campaign_end_date, b.campaign_end_date)', 'day') }} as overlap_days
    from campaigns as a
    inner join campaigns as b
        on a.campaign_id < b.campaign_id
        and a.campaign_start_date <= b.campaign_end_date
        and a.campaign_end_date >= b.campaign_start_date

),

final as (

    select
        o.campaign_a,
        o.campaign_a_name,
        o.campaign_b,
        o.campaign_b_name,
        o.overlap_start,
        o.overlap_end,
        o.overlap_days,
        ra.total_spend as campaign_a_roi,
        rb.total_spend as campaign_b_roi,
        ra.attributed_revenue as campaign_a_revenue,
        rb.attributed_revenue as campaign_b_revenue,
        case
            when o.overlap_days > 7 then 'significant_overlap'
            when o.overlap_days > 0 then 'minor_overlap'
            else 'no_overlap'
        end as overlap_severity
    from overlapping as o
    left join roi as ra on o.campaign_a = ra.campaign_id
    left join roi as rb on o.campaign_b = rb.campaign_id
    where o.overlap_days > 0

)

select * from final
