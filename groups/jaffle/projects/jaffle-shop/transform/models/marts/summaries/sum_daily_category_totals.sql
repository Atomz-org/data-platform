with 
ps as (
    select * from {{ ref('int_product_sales_by_location') }}
),

p as (
    select * from {{ ref('stg_products') }}
),

final as (
    select
        ps.sale_date,
        p.product_type as category,
        sum(ps.units_sold) as total_quantity,
        sum(ps.daily_revenue) as total_revenue,
        count(distinct ps.product_id) as active_products
    from ps
    inner join p on ps.product_id = p.product_id
    group by 1, 2
)
select * from final
