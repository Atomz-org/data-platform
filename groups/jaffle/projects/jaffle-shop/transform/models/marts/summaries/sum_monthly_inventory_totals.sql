with final as (
    select
        month_start,
        location_id,
        total_units_on_hand,
        monthly_movements,
        round(monthly_movements * 1.0 / nullif(total_units_on_hand, 0), 2) as turnover_ratio,
        lag(total_units_on_hand) over (partition by location_id order by month_start) as prior_month_value
    from {{ ref('met_monthly_inventory_metrics') }}
)
select * from final
