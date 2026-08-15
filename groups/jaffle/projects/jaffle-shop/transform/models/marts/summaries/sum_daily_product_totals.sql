with final as (
    select
        sale_date,
        product_id,
        units_sold,
        daily_revenue,
        round(daily_revenue * 1.0 / nullif(units_sold, 0), 2) as avg_unit_price,
        sum(daily_revenue) over (partition by product_id order by sale_date) as cumulative_revenue
    from {{ ref('fct_product_sales') }}
)
select * from final
