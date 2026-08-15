with final as (
    select
        week_start,
        product_id,
        weekly_units,
        weekly_revenue,
        round(weekly_revenue * 1.0 / nullif(weekly_units, 0), 2) as avg_unit_price,
        lag(weekly_revenue) over (partition by product_id order by week_start) as prior_week_revenue
    from {{ ref('met_weekly_product_sales') }}
)
select * from final
