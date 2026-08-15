with final as (
    select
        month_start,
        location_id,
        total_units_on_hand,
        monthly_movements,
        round(monthly_movements * 1.0 / nullif(total_units_on_hand, 0), 2) as turnover_ratio,
        case
            when monthly_movements * 1.0 / nullif(total_units_on_hand, 0) > 4 then 'fast'
            when monthly_movements * 1.0 / nullif(total_units_on_hand, 0) > 2 then 'moderate'
            else 'slow'
        end as turnover_band
    from {{ ref('met_monthly_inventory_metrics') }}
)
select * from final
