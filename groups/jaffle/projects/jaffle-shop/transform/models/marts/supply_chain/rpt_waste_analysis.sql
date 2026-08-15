with

waste_events as (

    select * from {{ ref('fct_waste_events') }}

),

waste_rates as (

    select * from {{ ref('int_waste_rate_by_product') }}

),

waste_summary as (

    select
        waste_events.product_id,
        waste_events.product_name,
        waste_events.product_type,
        waste_events.waste_reason,
        count(waste_events.waste_log_id) as event_count,
        sum(waste_events.quantity_wasted) as total_quantity_wasted,
        sum(waste_events.cost_of_waste) as total_cost_of_waste,
        avg(waste_events.quantity_wasted) as avg_quantity_per_event,
        min(waste_events.wasted_at) as first_waste_at,
        max(waste_events.wasted_at) as last_waste_at

    from waste_events

    group by
        waste_events.product_id,
        waste_events.product_name,
        waste_events.product_type,
        waste_events.waste_reason

),

final as (

    select
        waste_summary.product_id,
        waste_summary.product_name,
        waste_summary.product_type,
        waste_summary.waste_reason,
        waste_summary.event_count,
        waste_summary.total_quantity_wasted,
        waste_summary.total_cost_of_waste,
        waste_summary.avg_quantity_per_event,
        waste_summary.first_waste_at,
        waste_summary.last_waste_at,
        waste_rates.waste_rate,
        waste_rates.total_inbound_quantity

    from waste_summary

    -- NOTE: inner join to only show products that have inbound tracking
    inner join waste_rates
        on waste_summary.product_id = waste_rates.product_id

)

select * from final
