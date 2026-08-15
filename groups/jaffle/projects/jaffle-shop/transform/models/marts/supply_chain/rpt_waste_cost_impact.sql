with

waste_events as (

    select * from {{ ref('fct_waste_events') }}

),

products as (

    select * from {{ ref('stg_products') }}

),

waste_by_product_location as (

    select
        waste_events.product_id,
        waste_events.product_name,
        products.product_type,
        waste_events.location_id,
        waste_events.location_name,
        waste_events.waste_reason,
        count(waste_events.waste_log_id) as waste_event_count,
        sum(waste_events.quantity_wasted) as total_quantity_wasted,
        sum(waste_events.cost_of_waste) as total_waste_cost,
        avg(waste_events.cost_of_waste) as avg_waste_cost_per_event,
        min(waste_events.wasted_at) as first_waste_at,
        max(waste_events.wasted_at) as last_waste_at

    from waste_events

    left join products
        on waste_events.product_id = products.product_id

    group by
        waste_events.product_id,
        waste_events.product_name,
        products.product_type,
        waste_events.location_id,
        waste_events.location_name,
        waste_events.waste_reason

),

with_rankings as (

    select
        *,
        sum(total_waste_cost) over () as grand_total_waste_cost,
        case
            when sum(total_waste_cost) over () > 0
                then total_waste_cost * 1.0
                    / sum(total_waste_cost) over ()
            else 0
        end as waste_cost_share,
        rank() over (
            order by total_waste_cost desc
        ) as waste_cost_rank

    from waste_by_product_location

)

select * from with_rankings
