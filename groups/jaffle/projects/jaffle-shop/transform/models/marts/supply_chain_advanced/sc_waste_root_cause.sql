with

waste as (

    select
        waste_log_id,
        product_id,
        location_id,
        quantity_wasted,
        waste_reason,
        cost_of_waste,
        wasted_at
    from {{ ref('fct_waste_events') }}

),

final as (

    select
        {{ dbt.date_trunc('month', 'wasted_at') }} as waste_month,
        location_id,
        waste_reason,
        count(*) as waste_event_count,
        sum(quantity_wasted) as total_quantity_wasted,
        sum(cost_of_waste) as total_cost_of_waste,
        avg(cost_of_waste) as avg_cost_of_waste_per_event,
        case
            when waste_reason in ('expired', 'expiry', 'shelf_life') then 'overstock_expiry'
            when waste_reason in ('damaged', 'breakage', 'spill') then 'damage'
            when waste_reason in ('overproduction', 'surplus') then 'overproduction'
            when waste_reason in ('quality', 'quality_issue', 'contamination') then 'quality_issue'
            else 'other'
        end as root_cause_category
    from waste
    group by 1, 2, 3

)

select * from final
