with

product_sales_by_location as (

    select * from {{ ref('int_product_sales_by_location') }}

),

store_product_summary as (

    select
        location_id,
        location_name,
        product_id,
        product_name,
        product_type,
        sum(units_sold) as total_units_sold,
        sum(daily_revenue) as total_revenue,
        avg(units_sold) as avg_daily_units,
        count(distinct sale_date) as active_sale_days,
        min(sale_date) as first_sale_date,
        max(sale_date) as last_sale_date

    from product_sales_by_location
    group by
        location_id,
        location_name,
        product_id,
        product_name,
        product_type

),

with_ranks as (

    select
        *,
        rank() over (
            partition by location_id
            order by total_units_sold desc
        ) as volume_rank_at_store,
        rank() over (
            partition by location_id
            order by total_revenue desc
        ) as revenue_rank_at_store,
        total_revenue * 1.0 / nullif(
            sum(total_revenue) over (partition by location_id), 0
        ) * 100 as revenue_share_at_store

    from store_product_summary

)

select * from with_ranks
