with

velocity as (
    select
        product_id,
        product_name,
        product_type,
        avg(velocity_7d) as avg_velocity_7d,
        avg(velocity_28d) as avg_velocity_28d
    from {{ ref('int_product_sales_velocity') }}
    group by product_id, product_name, product_type
),

percentiles as (
    select
        percentile_cont(0.75) within group (order by avg_velocity_7d) as p75,
        percentile_cont(0.25) within group (order by avg_velocity_7d) as p25
    from velocity
),

final as (
    select
        v.product_id,
        v.product_name,
        v.product_type,
        v.avg_velocity_7d as daily_sales_velocity,
        v.avg_velocity_28d as monthly_sales_velocity,
        case
            when v.avg_velocity_7d >= pctl.p75 then 'fast_mover'
            when v.avg_velocity_7d >= pctl.p25 then 'medium_mover'
            else 'slow_mover'
        end as velocity_segment,
        case
            when v.avg_velocity_7d >= pctl.p75 then 'keep_high_stock'
            when v.avg_velocity_7d < pctl.p25 then 'reduce_stock'
            else 'maintain_current_stock'
        end as inventory_recommendation
    from velocity as v
    cross join percentiles as pctl
)

select * from final
