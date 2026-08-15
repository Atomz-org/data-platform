with

campaigns as (

    select * from {{ ref('stg_campaigns') }}

),

final as (

    select
        campaign_id,
        campaign_name,
        campaign_channel,
        campaign_status,
        campaign_description,
        budget,
        campaign_start_date,
        campaign_end_date,
        created_at,

        -- Derived fields
        case
            when campaign_status = 'active'
                and campaign_start_date <= current_date
                and (campaign_end_date >= current_date or campaign_end_date is null)
            then true
            else false
        end as is_currently_active,
        case
            when campaign_end_date is not null and campaign_start_date is not null
            then {{ dbt.datediff('campaign_start_date', 'campaign_end_date', 'day') }}
            else null
        end as campaign_duration_days

    from campaigns

)

select * from final
