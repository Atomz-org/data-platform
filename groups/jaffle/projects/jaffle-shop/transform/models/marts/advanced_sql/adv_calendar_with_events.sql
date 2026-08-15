-- adv_calendar_with_events.sql
-- Technique: UNION ALL to combine heterogeneous event sources onto a date spine
-- Joins util_date_spine with multiple event sources using UNION ALL to create an
-- annotated business calendar. Each event type (campaign, contract expiry) is
-- unioned into a common schema, then joined to the date spine so every calendar
-- day shows what business events are active or occurring.

with date_spine as (

    select * from {{ ref('util_date_spine') }}

),

-- Event source 1: Marketing campaigns (start and end dates)
campaign_events as (

    select
        campaign_start_date as event_date,
        'campaign_start' as event_type,
        campaign_name as event_name,
        campaign_id::text as event_source_id,
        'marketing' as event_category,
        campaign_channel as event_detail
    from {{ ref('dim_campaigns') }}
    where campaign_start_date is not null

    union all

    select
        campaign_end_date as event_date,
        'campaign_end' as event_type,
        campaign_name as event_name,
        campaign_id::text as event_source_id,
        'marketing' as event_category,
        campaign_channel as event_detail
    from {{ ref('dim_campaigns') }}
    where campaign_end_date is not null

),

-- Event source 2: Supplier contract expirations
contract_events as (

    select
        expiration_date as event_date,
        'contract_expiry' as event_type,
        'Contract #' || contract_id::text as event_name,
        contract_id::text as event_source_id,
        'supply_chain' as event_category,
        contract_type as event_detail
    from {{ ref('stg_supplier_contracts') }}
    where expiration_date is not null

    union all

    select
        effective_date as event_date,
        'contract_start' as event_type,
        'Contract #' || contract_id::text as event_name,
        contract_id::text as event_source_id,
        'supply_chain' as event_category,
        contract_type as event_detail
    from {{ ref('stg_supplier_contracts') }}
    where effective_date is not null

),

-- Combine all event sources via UNION ALL
all_events as (

    select * from campaign_events
    union all
    select * from contract_events

),

-- Aggregate distinct event types per day
-- (DuckDB listagg does not support DISTINCT; pre-dedup for compatibility)
daily_event_types as (

    select
        event_date,
        {% if target.type == 'snowflake' %}
        {{ sf_listagg("event_type", "', '", "order by event_type") }} as event_types
        {% else %}
        {{ sf_listagg("event_type", "', '", "order by event_type") }} as event_types
        {% endif %}
    from (
        select distinct event_date, event_type
        from all_events
    )
    group by 1

),

-- Aggregate distinct event categories per day
daily_event_categories as (

    select
        event_date,
        {% if target.type == 'snowflake' %}
        {{ sf_listagg("event_category", "', '", "order by event_category") }} as event_categories
        {% else %}
        {{ sf_listagg("event_category", "', '", "order by event_category") }} as event_categories
        {% endif %}
    from (
        select distinct event_date, event_category
        from all_events
    )
    group by 1

),

-- Count events per day for the calendar view
daily_event_summary as (

    select
        ae.event_date,
        count(*) as event_count,
        count(distinct ae.event_category) as category_count,
        det.event_types,
        dec2.event_categories
    from all_events as ae
    inner join daily_event_types as det
        on ae.event_date = det.event_date
    inner join daily_event_categories as dec2
        on ae.event_date = dec2.event_date
    group by 1, det.event_types, dec2.event_categories

),

-- Join to date spine to get a complete calendar with event annotations
calendar as (

    select
        ds.date_day,
        ds.day_name,
        ds.is_weekend,
        ds.week_start,
        ds.month_start,
        coalesce(des.event_count, 0) as event_count,
        des.category_count,
        des.event_types,
        des.event_categories,
        des.event_count is not null as has_events
    from date_spine as ds
    left join daily_event_summary as des
        on ds.date_day = des.event_date

)

select * from calendar
order by date_day
