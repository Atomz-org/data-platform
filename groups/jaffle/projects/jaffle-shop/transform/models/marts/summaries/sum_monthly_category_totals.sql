with 
ps as (
    select * from {{ ref('int_product_sales_by_location') }}
),

p as (
    select * from {{ ref('stg_products') }}
),

final as (
    select
        {{ sf_date_trunc('month', "ps.sale_date") }} as sale_month,
        p.product_type as category,
        sum(ps.units_sold) as total_quantity,
        sum(ps.daily_revenue) as total_revenue,
        count(distinct ps.product_id) as active_products,
        round(sum(ps.daily_revenue) * 100.0 / nullif(sum(sum(ps.daily_revenue)) over (
            partition by {{ sf_date_trunc('month', "ps.sale_date") }}
        ), 0), 2) as revenue_share_pct
    from ps
    inner join p on ps.product_id = p.product_id
    group by 1, 2
)
select * from final
