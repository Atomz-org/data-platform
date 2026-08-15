with monthly as (
    select month_start, location_id, total_units_on_hand, monthly_movements
    from {{ ref('met_monthly_inventory_metrics') }}
),
final as (
    select
        {{ sf_date_trunc('quarter', "month_start") }} as metric_quarter,
        location_id,
        round(avg(total_units_on_hand), 2) as avg_quarterly_value,
        sum(monthly_movements) as quarterly_movement,
        round(sum(monthly_movements) * 1.0 / nullif(avg(total_units_on_hand), 0), 2) as quarterly_turnover
    from monthly
    group by 1, 2
)
select * from final
