with

ps as (
    select * from {{ ref('fct_product_sales') }}
)


select
    ps.product_id,
    ps.product_name,
    sum(ps.daily_revenue) as total_revenue
from ps
group by ps.product_id, ps.product_name
order by total_revenue asc
limit 5
