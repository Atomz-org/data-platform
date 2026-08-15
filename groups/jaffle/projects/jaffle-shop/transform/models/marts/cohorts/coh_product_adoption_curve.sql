with

product_sales as (

    select * from {{ ref('fct_product_sales') }}

),

product_first_sale as (

    select
        product_id,
        product_name,
        product_type,
        min(sale_date) as first_sale_date
    from product_sales
    group by 1, 2, 3

),

daily_adoption as (

    select
        ps.product_id,
        ps.product_name,
        pfs.first_sale_date,
        ps.sale_date,
        {{ dbt.datediff('pfs.first_sale_date', 'ps.sale_date', 'day') }} as days_since_launch,
        ps.units_sold,
        ps.order_count,
        ps.daily_revenue
    from product_sales as ps
    inner join product_first_sale as pfs
        on ps.product_id = pfs.product_id

),

adoption_milestones as (

    select
        product_id,
        product_name,
        first_sale_date,
        sum(case when days_since_launch <= 30 then units_sold else 0 end) as units_first_30d,
        sum(case when days_since_launch <= 60 then units_sold else 0 end) as units_first_60d,
        sum(case when days_since_launch <= 90 then units_sold else 0 end) as units_first_90d,
        sum(case when days_since_launch <= 180 then units_sold else 0 end) as units_first_180d,
        sum(case when days_since_launch <= 30 then order_count else 0 end) as orders_first_30d,
        sum(case when days_since_launch <= 60 then order_count else 0 end) as orders_first_60d,
        sum(case when days_since_launch <= 90 then order_count else 0 end) as orders_first_90d,
        sum(case when days_since_launch <= 180 then order_count else 0 end) as orders_first_180d,
        sum(case when days_since_launch <= 30 then daily_revenue else 0 end) as revenue_first_30d,
        sum(case when days_since_launch <= 90 then daily_revenue else 0 end) as revenue_first_90d,
        sum(case when days_since_launch <= 180 then daily_revenue else 0 end) as revenue_first_180d,
        sum(units_sold) as total_units_all_time,
        max(days_since_launch) as days_on_market
    from daily_adoption
    group by 1, 2, 3

)

select * from adoption_milestones
