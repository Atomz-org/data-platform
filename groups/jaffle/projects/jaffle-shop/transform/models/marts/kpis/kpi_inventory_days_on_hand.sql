with final as (
    select
        product_id,
        location_id,
        days_on_hand,
        case
            when days_on_hand < 3 then 'critical'
            when days_on_hand < 7 then 'low'
            when days_on_hand < 30 then 'healthy'
            else 'excess'
        end as doh_status
    from {{ ref('sc_inventory_days_on_hand') }}
)
select * from final
