with

ps as (
    select * from {{ ref('fct_product_sales') }}
),

product_sales as (

    select
        ps.product_id,
        null::text,
        ps.sale_date,
        ps.daily_revenue,
        ps.units_sold
    from ps

),

products as (

    select
        product_id,
        product_name,
        product_type
    from {{ ref('stg_products') }}

),

monthly_by_type as (

    select
        {{ dbt.date_trunc('month', 'ps.sale_date') }} as sale_month,
        p.product_type,
        sum(ps.daily_revenue) as type_revenue,
        sum(ps.units_sold) as type_quantity
    from product_sales as ps
    inner join products as p on ps.product_id = p.product_id
    group by 1, 2

),

monthly_total as (

    select
        sale_month,
        sum(type_revenue) as total_revenue
    from monthly_by_type
    group by 1

),

with_share as (

    select
        m.sale_month,
        m.product_type,
        m.type_revenue,
        m.type_quantity,
        mt.total_revenue,
        case
            when mt.total_revenue > 0
            then m.type_revenue / mt.total_revenue * 100
            else 0
        end as revenue_share_pct,
        lag(
            case when mt.total_revenue > 0 then m.type_revenue / mt.total_revenue * 100 else 0 end,
            1
        ) over (partition by m.product_type order by m.sale_month) as prev_month_share_pct
    from monthly_by_type as m
    inner join monthly_total as mt on m.sale_month = mt.sale_month

)

select
    sale_month,
    product_type,
    type_revenue,
    type_quantity,
    total_revenue,
    revenue_share_pct,
    prev_month_share_pct,
    revenue_share_pct - coalesce(prev_month_share_pct, revenue_share_pct) as share_shift_pct
from with_share
