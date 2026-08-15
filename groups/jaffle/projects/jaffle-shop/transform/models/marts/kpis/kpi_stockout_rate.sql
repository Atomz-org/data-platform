with stockout_events as (
    select
        {{ sf_date_trunc('month', "moved_at") }} as metric_month,
        location_id,
        count(distinct case when movement_type = 'stockout' then product_id end) as stockout_products,
        count(distinct product_id) as total_products
    from {{ ref('fct_inventory_movements') }}
    group by 1, 2
),
final as (
    select
        metric_month,
        location_id,
        stockout_products,
        total_products,
        round(stockout_products * 100.0 / nullif(total_products, 0), 2) as stockout_rate_pct
    from stockout_events
)
select * from final
