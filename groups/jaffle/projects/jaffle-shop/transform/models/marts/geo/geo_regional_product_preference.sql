with

product_sales as (
    select * from {{ ref('int_product_sales_by_location') }}
),

store_product_sales as (
    select
        location_id,
        location_name as store_name,
        product_id,
        sum(units_sold) as total_quantity,
        sum(daily_revenue) as total_sales
    from product_sales
    group by location_id, location_name, product_id
),

store_total as (
    select
        location_id,
        sum(total_sales) as store_total_sales
    from store_product_sales
    group by location_id
),

product_mix as (
    select
        sps.location_id,
        sps.store_name,
        sps.product_id,
        sps.total_quantity,
        sps.total_sales,
        st.store_total_sales,
        round(sps.total_sales * 100.0 / nullif(st.store_total_sales, 0), 2) as sales_mix_pct,
        row_number() over (
            partition by sps.location_id
            order by sps.total_sales desc
        ) as product_rank
    from store_product_sales sps
    left join store_total st on sps.location_id = st.location_id
)

select * from product_mix
